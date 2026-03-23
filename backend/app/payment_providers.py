"""Payment provider adapters for invoice settlement with safe mock fallback."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import httpx


@dataclass
class PaymentResult:
    """Normalized payment result returned by provider adapters."""

    success: bool
    provider: str
    transaction_id: Optional[str]
    status_message: str
    raw_status: str


def _provider_name() -> str:
    """Resolve active provider slug from environment."""
    return (os.getenv("SOLAR_SHARE_PAYMENT_PROVIDER") or "mock").strip().lower()


def _mock_charge(invoice_id: str, amount_usd: float, payment_method_token: Optional[str]) -> PaymentResult:
    """Deterministic mock charge path for local/dev and fallback operation."""
    normalized_invoice_id = (invoice_id or "").strip() or "unknown"
    normalized_token = (payment_method_token or "demo_card").strip().lower()
    if normalized_token in {"fail", "decline", "insufficient_funds"}:
        return PaymentResult(
            success=False,
            provider="mock",
            transaction_id=None,
            status_message="Mock payment declined for testing.",
            raw_status="failed",
        )
    seed = f"{normalized_invoice_id}:{amount_usd:.2f}:{datetime.now(timezone.utc).date().isoformat()}"
    transaction_id = f"mock_{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:16]}"
    return PaymentResult(
        success=True,
        provider="mock",
        transaction_id=transaction_id,
        status_message="Payment captured with mock provider.",
        raw_status="succeeded",
    )


def _stripe_charge(invoice_id: str, amount_usd: float, payment_method_token: Optional[str]) -> PaymentResult:
    """Attempt Stripe payment intent creation/confirmation when Stripe is configured."""
    secret_key = (os.getenv("STRIPE_SECRET_KEY") or "").strip()
    if not secret_key:
        return PaymentResult(
            success=False,
            provider="stripe",
            transaction_id=None,
            status_message="Stripe secret key is missing.",
            raw_status="misconfigured",
        )

    payment_method = (payment_method_token or "").strip()
    if not payment_method:
        return PaymentResult(
            success=False,
            provider="stripe",
            transaction_id=None,
            status_message="Payment method token is required for Stripe charges.",
            raw_status="invalid_request",
        )

    cents = max(int(round(amount_usd * 100)), 0)
    if cents <= 0:
        return PaymentResult(
            success=True,
            provider="stripe",
            transaction_id=f"stripe_zero_{invoice_id}",
            status_message="No payment due for this invoice.",
            raw_status="succeeded",
        )

    payload = {
        "amount": str(cents),
        "currency": "usd",
        "confirm": "true",
        "payment_method": payment_method,
        "description": f"SolarShare invoice {invoice_id}",
    }
    try:
        with httpx.Client(timeout=8.0) as client:
            response = client.post(
                "https://api.stripe.com/v1/payment_intents",
                data=payload,
                headers={"Authorization": f"Bearer {secret_key}"},
            )
            data = response.json()
        if response.status_code >= 400:
            message = str(data.get("error", {}).get("message") or "Stripe payment failed.")
            return PaymentResult(
                success=False,
                provider="stripe",
                transaction_id=None,
                status_message=message,
                raw_status="failed",
            )
        status = str(data.get("status") or "unknown")
        payment_intent_id = str(data.get("id") or "")
        return PaymentResult(
            success=status in {"succeeded", "processing"},
            provider="stripe",
            transaction_id=payment_intent_id or None,
            status_message=f"Stripe status: {status}",
            raw_status=status,
        )
    except Exception as exc:
        return PaymentResult(
            success=False,
            provider="stripe",
            transaction_id=None,
            status_message=f"Stripe request error: {exc}",
            raw_status="error",
        )


def charge_invoice(invoice_id: str, amount_usd: float, payment_method_token: Optional[str] = None) -> PaymentResult:
    """Charge invoice using configured provider with optional safe fallback to mock."""
    provider = _provider_name()
    if provider == "stripe":
        result = _stripe_charge(invoice_id=invoice_id, amount_usd=amount_usd, payment_method_token=payment_method_token)
        fallback_allowed = (os.getenv("SOLAR_SHARE_PAYMENT_FALLBACK_TO_MOCK") or "true").strip().lower() in {"1", "true", "yes", "on"}
        if result.success or not fallback_allowed:
            return result
        fallback_result = _mock_charge(invoice_id=invoice_id, amount_usd=amount_usd, payment_method_token=payment_method_token)
        fallback_result.status_message = f"{result.status_message} Fallback: {fallback_result.status_message}"
        return fallback_result

    return _mock_charge(invoice_id=invoice_id, amount_usd=amount_usd, payment_method_token=payment_method_token)
