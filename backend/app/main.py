# backend/app/main.py
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.schemas import (
    UserRequest,
    ScoredOptionSchema,
    RecommendationResponse,
)
from app.logic import get_ranked_options, get_recommendation

app = FastAPI(
    title="Solar Share Backend",
    description="Decision engine for local clean energy optimization",
    version="0.1.0",
)

# CORS: allow frontend apps to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ok for class demo; lock down later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# Demo data for SolarShare model
# -------------------------
TERRITORIES: Dict[str, Dict[str, str]] = {
    "pseg-li": {"territory_id": "pseg-li", "territory_name": "PSEG Long Island"}
}

# Minimal realistic project fields your frontend needs
PROJECTS: List[Dict[str, Any]] = [
    {
        "project_id": "northport-sun-01",
        "name": "Northport Community Solar",
        "town": "Northport, NY",
        "credit_rate": 0.16,
        "subscriber_pay_pct": 0.90,
        "status": "Open",
    },
    {
        "project_id": "huntington-green-02",
        "name": "Huntington Green Credits",
        "town": "Huntington, NY",
        "credit_rate": 0.17,
        "subscriber_pay_pct": 0.92,
        "status": "Limited",
    },
    {
        "project_id": "babylon-solar-03",
        "name": "Babylon Solar Collective",
        "town": "Babylon, NY",
        "credit_rate": 0.155,
        "subscriber_pay_pct": 0.90,
        "status": "Open",
    },
]

# In-memory enrollments for demo purposes
ENROLLMENTS: Dict[str, Dict[str, Any]] = {}


def _is_pseg_li_zip(zip_code: str) -> bool:
    z = zip_code.strip()
    # Demo rule for Long Island zips (matches what you used earlier)
    return len(z) == 5 and z.isdigit() and z[:3] in {"115", "117", "119"}


def _find_project(project_id: str) -> Optional[Dict[str, Any]]:
    for p in PROJECTS:
        if p["project_id"] == project_id:
            return p
    return None


def _calc_estimate(project: Dict[str, Any], monthly_usage_kwh: float) -> Dict[str, float]:
    credit_value = float(monthly_usage_kwh) * float(project["credit_rate"])
    subscriber_pays = credit_value * float(project["subscriber_pay_pct"])
    savings = max(credit_value - subscriber_pays, 0.0)

    # rounded for clean UI
    return {
        "credit_value": round(credit_value, 2),
        "subscriber_pays": round(subscriber_pays, 2),
        "savings": round(savings, 2),
    }


# -------------------------
# Existing endpoints (keep)
# -------------------------
@app.get("/")
def health_check():
    return {
        "status": "ok",
        "message": "Solar Share backend is running",
        "version": "0.1.0",
    }


@app.post("/options", response_model=List[ScoredOptionSchema])
def options(request: UserRequest):
    return get_ranked_options(request)


@app.post("/recommendation", response_model=RecommendationResponse)
def recommendation(request: UserRequest):
    return get_recommendation(request)


# -------------------------
# New SolarShare API (React expects these)
# -------------------------
class EligibilityIn(BaseModel):
    zip: str = Field(..., min_length=5, max_length=5)


class EligibilityOut(BaseModel):
    eligible: bool
    territory_id: Optional[str] = None
    territory_name: Optional[str] = None


@app.post("/api/check-eligibility", response_model=EligibilityOut)
def api_check_eligibility(payload: EligibilityIn):
    if not _is_pseg_li_zip(payload.zip):
        return EligibilityOut(eligible=False)

    t = TERRITORIES["pseg-li"]
    return EligibilityOut(
        eligible=True,
        territory_id=t["territory_id"],
        territory_name=t["territory_name"],
    )


class ProjectOut(BaseModel):
    project_id: str
    name: str
    town: str
    credit_rate: float
    subscriber_pay_pct: float
    status: str


@app.get("/api/projects", response_model=List[ProjectOut])
def api_projects(territory_id: str = Query(...)):
    # For the demo, only PSEG LI is supported
    if territory_id != "pseg-li":
        return []
    return PROJECTS


class EstimateIn(BaseModel):
    zip: str = Field(..., min_length=5, max_length=5)
    monthly_usage_kwh: float = Field(..., gt=0)
    project_id: str


class EstimateOut(BaseModel):
    credit_value: float
    subscriber_pays: float
    savings: float


@app.post("/api/estimate", response_model=EstimateOut)
def api_estimate(payload: EstimateIn):
    if not _is_pseg_li_zip(payload.zip):
        raise HTTPException(status_code=400, detail="ZIP not eligible for supported territory")

    project = _find_project(payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return _calc_estimate(project, payload.monthly_usage_kwh)


class EnrollIn(BaseModel):
    zip: str = Field(..., min_length=5, max_length=5)
    territory_id: str
    project_id: str

    name: str
    email: str
    address: str

    monthly_usage_kwh: Optional[float] = Field(default=None, gt=0)

    consent_no_roof_changes: bool = True
    consent_no_utility_switching: bool = True
    consent_cancel_anytime: bool = True


class EnrollOut(BaseModel):
    enrollment_id: str


@app.post("/api/enroll", response_model=EnrollOut)
def api_enroll(payload: EnrollIn):
    if payload.territory_id != "pseg-li":
        raise HTTPException(status_code=400, detail="Unsupported territory_id")

    if not _is_pseg_li_zip(payload.zip):
        raise HTTPException(status_code=400, detail="ZIP not eligible for supported territory")

    project = _find_project(payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    enrollment_id = uuid4().hex

    # status flow for demo
    status = "submitted"

    est = None
    if payload.monthly_usage_kwh is not None:
        est = _calc_estimate(project, payload.monthly_usage_kwh)

    ENROLLMENTS[enrollment_id] = {
        "enrollment_id": enrollment_id,
        "status": status,
        "zip": payload.zip,
        "territory_id": payload.territory_id,
        "territory_name": TERRITORIES["pseg-li"]["territory_name"],
        "project": project,
        "name": payload.name,
        "email": payload.email,
        "address": payload.address,
        "monthly_usage_kwh": payload.monthly_usage_kwh,
        "estimate": est,
        "expected_credit_start": "1–2 billing cycles",
    }

    return EnrollOut(enrollment_id=enrollment_id)


class EnrollmentOut(BaseModel):
    enrollment_id: str
    status: str
    territory_name: str
    project: ProjectOut
    monthly_usage_kwh: Optional[float] = None
    estimate: Optional[EstimateOut] = None
    expected_credit_start: str


@app.get("/api/enrollment", response_model=EnrollmentOut)
def api_get_enrollment(enrollment_id: str = Query(...)):
    e = ENROLLMENTS.get(enrollment_id)
    if not e:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    return {
        "enrollment_id": e["enrollment_id"],
        "status": e["status"],
        "territory_name": e["territory_name"],
        "project": e["project"],
        "monthly_usage_kwh": e["monthly_usage_kwh"],
        "estimate": e["estimate"],
        "expected_credit_start": e["expected_credit_start"],
    }