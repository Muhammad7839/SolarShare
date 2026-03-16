"""Assistant reply service with AI-first behavior and deterministic fallback."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

import httpx


def _network_enabled() -> bool:
    """Gate outbound AI calls for tests and offline deployments."""
    if os.getenv("PYTEST_CURRENT_TEST"):
        return False
    if os.getenv("SOLAR_SHARE_ASSISTANT_DISABLE_NETWORK", "0") == "1":
        return False
    return True


def _fallback_response(message: str) -> Tuple[str, List[str]]:
    """Return deterministic navigation help when AI is unavailable."""
    normalized = message.lower()
    if "compare" in normalized or "run" in normalized:
        return (
            "Open Run Live Comparison, provide location or ZIP, usage, and priority, then submit to see ranked options.",
            ["Go to comparison form", "See ranked options", "Save scenario"],
        )
    if "zip" in normalized or "location" in normalized or "city" in normalized:
        return (
            "Use ZIP for higher precision. Results will show resolved city, county, state, postal code, and confidence.",
            ["Enter ZIP", "Preview location", "Run comparison"],
        )
    if "cinematic" in normalized or "theme" in normalized or "light" in normalized:
        return (
            "Use the Cinematic Mode button in the header. Theme preference is retained across page navigation.",
            ["Toggle cinematic", "Continue browsing"],
        )
    if "contact" in normalized or "support" in normalized:
        return (
            "Use the Contact page to submit customer, partnership, or investor inquiries. Messages route to the operations inbox.",
            ["Open contact page", "Submit inquiry"],
        )
    return (
        "I can help with comparison flow, location input, theme settings, and where to find key sections.",
        ["Run comparison", "Location help", "Contact support"],
    )


def _ai_reply(message: str, page: str | None, context: Dict[str, Any]) -> str | None:
    """Attempt AI response via configurable OpenAI-compatible endpoint."""
    api_key = os.getenv("SOLAR_SHARE_AI_API_KEY")
    if not api_key or not _network_enabled():
        return None

    model = os.getenv("SOLAR_SHARE_AI_MODEL", "gpt-4o-mini")
    base_url = os.getenv("SOLAR_SHARE_AI_BASE_URL", "https://api.openai.com/v1")
    url = f"{base_url.rstrip('/')}/chat/completions"

    system_prompt = (
        "You are the SolarShare website assistant. Keep answers concise, practical, and navigation-focused. "
        "Prioritize helping first-time users complete comparison flow and understand location accuracy signals."
    )
    user_context = {
        "page": page,
        "context": context,
        "message": message,
    }

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(
                url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": str(user_context)},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 240,
                },
            )
            response.raise_for_status()
            payload = response.json()
        choices = payload.get("choices", [])
        if not choices:
            return None
        content = choices[0].get("message", {}).get("content")
        if not isinstance(content, str):
            return None
        return content.strip()
    except Exception:
        return None


def build_assistant_reply(message: str, page: str | None, context: Dict[str, Any]) -> Dict[str, Any]:
    """Return assistant reply payload with AI mode fallback guarantees."""
    ai_text = _ai_reply(message=message, page=page, context=context)
    if ai_text:
        _, actions = _fallback_response(message)
        return {"reply": ai_text, "mode": "ai", "suggested_actions": actions}

    fallback_text, actions = _fallback_response(message)
    return {"reply": fallback_text, "mode": "fallback", "suggested_actions": actions}
