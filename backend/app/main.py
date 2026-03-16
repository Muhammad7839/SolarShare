"""FastAPI application entrypoints and HTTP-facing request handling."""

import json
import logging
import os
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Deque, Dict, List, Tuple
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.assistant_service import build_assistant_reply
from app.contact_store import init_contact_store, insert_contact_inquiry
from app.ops_store import (
    get_admin_analytics_summary,
    init_ops_store,
    insert_analytics_event,
    insert_crm_lead,
)
from app.real_data import resolve_location_context
from app.schemas import (
    AdminAnalyticsOut,
    AnalyticsEventIn,
    AnalyticsEventOut,
    AssistantChatIn,
    AssistantChatOut,
    ContactInquiryIn,
    ContactInquiryOut,
    DemoRequestIn,
    DemoRequestOut,
    LocationResolveIn,
    LocationResolveOut,
    UserRequest,
    ScoredOptionSchema,
    LiveComparisonResponse,
    RecommendationResponse,
)
from app.logic import get_live_comparison, get_ranked_options, get_recommendation


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    """Initialize persistent stores once when API process starts."""
    init_contact_store()
    init_ops_store()
    yield


app = FastAPI(
    title="Solar Share Backend",
    description="Decision engine for local clean energy optimization",
    version="0.1.0",
    lifespan=app_lifespan,
)

logger = logging.getLogger("solarshare.api")
if not logger.handlers:
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)
logger.propagate = False

RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("SOLAR_SHARE_RATE_LIMIT_WINDOW_SECONDS", "60"))
LIVE_COMPARISON_RATE_LIMIT = int(os.getenv("SOLAR_SHARE_RATE_LIMIT_LIVE_COMPARISON_PER_MIN", "60"))
CONTACT_RATE_LIMIT = int(os.getenv("SOLAR_SHARE_RATE_LIMIT_CONTACT_PER_MIN", "20"))
ASSISTANT_RATE_LIMIT = int(os.getenv("SOLAR_SHARE_RATE_LIMIT_ASSISTANT_PER_MIN", "80"))
ANALYTICS_RATE_LIMIT = int(os.getenv("SOLAR_SHARE_RATE_LIMIT_ANALYTICS_PER_MIN", "200"))
TRUST_PROXY_HEADERS = os.getenv("SOLAR_SHARE_TRUST_PROXY_HEADERS", "0") == "1"
_RATE_LIMIT_BUCKETS: Dict[Tuple[str, str], Deque[float]] = defaultdict(deque)
_RATE_LIMIT_LOCK = threading.Lock()
STATIC_DIR = Path(__file__).resolve().parent / "static"


def _get_cors_origins() -> List[str]:
    """Read allowed CORS origins from env, with local dev defaults."""
    configured_origins = os.getenv("SOLAR_SHARE_CORS_ORIGINS")
    if configured_origins:
        return [origin.strip() for origin in configured_origins.split(",") if origin.strip()]

    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


# CORS: allow frontend apps to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _client_identifier(request: Request) -> str:
    """Resolve stable client key for simple in-memory rate limiting."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if TRUST_PROXY_HEADERS and forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _enforce_rate_limit(request: Request, bucket: str, limit: int) -> None:
    """Apply per-client fixed-window limit for high-traffic public endpoints."""
    if limit <= 0:
        return
    now = time.monotonic()
    key = (bucket, _client_identifier(request))
    window_start = now - RATE_LIMIT_WINDOW_SECONDS
    with _RATE_LIMIT_LOCK:
        requests = _RATE_LIMIT_BUCKETS[key]
        while requests and requests[0] < window_start:
            requests.popleft()
        if len(requests) >= limit:
            raise HTTPException(status_code=429, detail="Too many requests. Please retry shortly.")
        requests.append(now)


@app.middleware("http")
async def request_tracing_middleware(request: Request, call_next):
    """Attach request IDs and emit structured access logs for observability."""
    request_id = request.headers.get("x-request-id") or uuid4().hex
    request.state.request_id = request_id
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.exception(
            json.dumps(
                {
                    "event": "request_error",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                }
            )
        )
        raise

    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    response.headers["X-Request-ID"] = request_id
    logger.info(
        json.dumps(
            {
                "event": "http_request",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            }
        )
    )
    return response


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "Solar Share backend is running",
        "version": "0.1.0",
    }


# Serve the web frontend from the backend for a single deployable app.
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _serve_page(filename: str):
    """Return a static HTML page from app/static by filename."""
    return FileResponse(str(STATIC_DIR / filename))


@app.get("/")
@app.get("/app")
def web_app():
    return _serve_page("index.html")


@app.get("/about")
def about_page():
    return _serve_page("about.html")


@app.get("/methodology")
def methodology_page():
    return _serve_page("methodology.html")


@app.get("/pricing")
def pricing_page():
    return _serve_page("pricing.html")


@app.get("/contact")
def contact_page():
    return _serve_page("contact.html")


@app.get("/admin")
def admin_page():
    return _serve_page("admin.html")


@app.post("/options", response_model=List[ScoredOptionSchema])
def options(request: UserRequest):
    return get_ranked_options(request)


@app.post("/recommendation", response_model=RecommendationResponse)
def recommendation(request: UserRequest):
    try:
        return get_recommendation(request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/live-comparison", response_model=LiveComparisonResponse)
def live_comparison(request: UserRequest, http_request: Request):
    """Return one combined payload with live market context and recommendations."""
    _enforce_rate_limit(http_request, "live-comparison", LIVE_COMPARISON_RATE_LIMIT)
    try:
        payload = get_live_comparison(request)
        logger.info(
            json.dumps(
                {
                    "event": "live_comparison_completed",
                    "request_id": getattr(http_request.state, "request_id", None),
                    "priority": request.priority,
                    "using_fallback": payload.get("market_context", {}).get("using_fallback"),
                    "state_code": payload.get("market_context", {}).get("state_code"),
                }
            )
        )
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/location-resolve", response_model=LocationResolveOut)
def location_resolve(payload: LocationResolveIn, http_request: Request):
    """Resolve and normalize location metadata for pre-submit UX previews."""
    _enforce_rate_limit(http_request, "location-resolve", LIVE_COMPARISON_RATE_LIMIT)
    result = resolve_location_context(payload.location, payload.zip_code)
    logger.info(
        json.dumps(
            {
                "event": "location_resolve_completed",
                "request_id": getattr(http_request.state, "request_id", None),
                "using_fallback": result.get("using_fallback"),
                "state_code": result.get("state_code"),
                "source": result.get("source"),
            }
        )
    )
    return result


@app.post("/assistant-chat", response_model=AssistantChatOut)
def assistant_chat(payload: AssistantChatIn, http_request: Request):
    """Return AI-first assistant responses with deterministic fallback behavior."""
    _enforce_rate_limit(http_request, "assistant-chat", ASSISTANT_RATE_LIMIT)
    try:
        insert_analytics_event(
            event_name="chatbot_message",
            page=payload.page,
            session_id=str(payload.context.get("session_id") or ""),
            metadata={"input_length": len(payload.message)},
        )
    except Exception:
        logger.exception(
            json.dumps(
                {
                    "event": "analytics_write_failed",
                    "request_id": getattr(http_request.state, "request_id", None),
                    "path": http_request.url.path,
                }
            )
        )
    response_payload = build_assistant_reply(payload.message, payload.page, payload.context)
    logger.info(
        json.dumps(
            {
                "event": "assistant_chat_completed",
                "request_id": getattr(http_request.state, "request_id", None),
                "mode": response_payload.get("mode"),
                "page": payload.page,
            }
        )
    )
    return response_payload


@app.post("/analytics/events", response_model=AnalyticsEventOut)
def analytics_events(payload: AnalyticsEventIn, http_request: Request):
    """Accept anonymous conversion instrumentation events for admin funnel analytics."""
    _enforce_rate_limit(http_request, "analytics-events", ANALYTICS_RATE_LIMIT)
    try:
        insert_analytics_event(
            event_name=payload.event_name,
            page=payload.page,
            session_id=payload.session_id,
            metadata=payload.metadata,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Unable to persist analytics event") from exc
    return {"accepted": True}


@app.get("/admin/analytics", response_model=AdminAnalyticsOut)
def admin_analytics(_: Request):
    """Return aggregate analytics and drop-off summary for operations view."""
    return get_admin_analytics_summary()


@app.post("/contact-inquiries", response_model=ContactInquiryOut)
def contact_inquiries(payload: ContactInquiryIn, http_request: Request):
    """Accept validated website inquiries for follow-up workflow."""
    _enforce_rate_limit(http_request, "contact-inquiries", CONTACT_RATE_LIMIT)
    try:
        inquiry_id = insert_contact_inquiry(
            name=payload.name,
            email=str(payload.email),
            interest=payload.interest,
            message=payload.message,
        )
        insert_crm_lead(
            source="contact_inquiry",
            name=payload.name,
            email=str(payload.email),
            organization=None,
            message=payload.message,
            payload={
                "interest": payload.interest,
                "inquiry_id": inquiry_id,
            },
        )
        insert_analytics_event(
            event_name="contact_submit",
            page="/contact",
            session_id=http_request.headers.get("x-session-id"),
            metadata={"interest": payload.interest},
        )
    except Exception as exc:
        logger.exception(
            json.dumps(
                {
                    "event": "contact_inquiry_write_failed",
                    "request_id": getattr(http_request.state, "request_id", None),
                    "path": http_request.url.path,
                }
            )
        )
        raise HTTPException(
            status_code=503,
            detail="Inquiry service temporarily unavailable. Please retry shortly.",
        ) from exc

    logger.info(
        json.dumps(
            {
                "event": "contact_inquiry_received",
                "request_id": getattr(http_request.state, "request_id", None),
                "inquiry_id": inquiry_id,
                "interest": payload.interest,
            }
        )
    )
    return {"inquiry_id": inquiry_id, "received": True}


@app.post("/demo-requests", response_model=DemoRequestOut)
def demo_requests(payload: DemoRequestIn, http_request: Request):
    """Accept demo request submissions and normalize them into CRM lead storage."""
    _enforce_rate_limit(http_request, "demo-requests", CONTACT_RATE_LIMIT)
    try:
        lead_id = insert_crm_lead(
            source="demo_request",
            name=payload.name,
            email=str(payload.email),
            organization=payload.organization,
            message=payload.message,
            payload={
                "organization": payload.organization,
                "request_path": str(http_request.url.path),
            },
        )
        insert_analytics_event(
            event_name="demo_request_submit",
            page="/",
            session_id=http_request.headers.get("x-session-id"),
            metadata={"organization": payload.organization or ""},
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Demo request service temporarily unavailable.") from exc
    logger.info(
        json.dumps(
            {
                "event": "demo_request_received",
                "request_id": getattr(http_request.state, "request_id", None),
                "lead_id": lead_id,
            }
        )
    )
    return {"lead_id": lead_id, "received": True}
