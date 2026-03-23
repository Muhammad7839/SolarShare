"""Billing service helpers for payment processing and invoice lifecycle actions."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.payment_providers import charge_invoice
from app.project_store import get_invoice_for_user_id, update_invoice_status_for_user_id


def pay_invoice_for_user(user_id: str, invoice_id: str, payment_method_token: Optional[str]) -> Dict[str, Any]:
    """Charge invoice using configured provider and persist lifecycle outcome."""
    invoice = get_invoice_for_user_id(user_id=user_id, invoice_id=invoice_id)
    if not invoice:
        return {"ok": False, "error": "Invoice not found"}

    current_status = str(invoice.get("status") or "")
    if current_status == "paid":
        return {
            "ok": True,
            "invoice_id": invoice_id,
            "status": "paid",
            "payment_provider": invoice.get("payment_provider"),
            "payment_transaction_id": invoice.get("payment_transaction_id"),
            "message": "Invoice already paid.",
        }

    payment_due = float(invoice.get("payment_due") or 0.0)
    if payment_due <= 0:
        update_invoice_status_for_user_id(
            user_id=user_id,
            invoice_id=invoice_id,
            status="paid",
            payment_provider="none",
            payment_transaction_id="zero_due",
            payment_status_message="No payment due for invoice.",
        )
        return {
            "ok": True,
            "invoice_id": invoice_id,
            "status": "paid",
            "payment_provider": "none",
            "payment_transaction_id": "zero_due",
            "message": "Invoice had no payment due.",
        }

    result = charge_invoice(
        invoice_id=invoice_id,
        amount_usd=payment_due,
        payment_method_token=payment_method_token,
    )
    new_status = "paid" if result.success else "failed"
    update_invoice_status_for_user_id(
        user_id=user_id,
        invoice_id=invoice_id,
        status=new_status,
        payment_provider=result.provider,
        payment_transaction_id=result.transaction_id,
        payment_status_message=result.status_message,
    )
    return {
        "ok": bool(result.success),
        "invoice_id": invoice_id,
        "status": new_status,
        "payment_provider": result.provider,
        "payment_transaction_id": result.transaction_id,
        "message": result.status_message,
        "raw_status": result.raw_status,
    }
