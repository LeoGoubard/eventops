"""Stripe sync: turn webhook deliveries into sales attributed to an event.

Attribution relies on one convention: the Checkout Session (or the Payment Link that
creates it) carries `metadata.eventops_event_id`, the id of the EventOps event whose
replay or offer page sent the buyer to checkout.
"""

import hashlib
import hmac
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from django.db.models import Count, Sum

from apps.events.models import Event
from apps.sales.models import Sale

METADATA_KEY = "eventops_event_id"
SIGNATURE_TOLERANCE_SECONDS = 300


class InvalidSignature(Exception):
    pass


def verify_signature(payload: bytes, header: str, secret: str, now: float | None = None) -> None:
    """Check a `Stripe-Signature` header (scheme v1: HMAC-SHA256 of "<timestamp>.<body>").

    Raises InvalidSignature when the header is malformed, the signature does not match,
    or the timestamp is too old (which blocks replays of a captured request).
    """
    timestamp = ""
    candidates: list[str] = []
    for part in header.split(","):
        key, _, value = part.strip().partition("=")
        if key == "t":
            timestamp = value
        elif key == "v1":
            candidates.append(value)
    if not timestamp.isdigit() or not candidates:
        raise InvalidSignature("Malformed Stripe-Signature header.")

    signed = timestamp.encode() + b"." + payload
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, candidate) for candidate in candidates):
        raise InvalidSignature("Signature does not match.")

    current = time.time() if now is None else now
    if abs(current - int(timestamp)) > SIGNATURE_TOLERANCE_SECONDS:
        raise InvalidSignature("Timestamp outside the tolerance window.")


def handle_stripe_event(event: dict[str, Any]) -> str:
    """Apply one Stripe event. Returns a short outcome, useful in logs and tests.

    Stripe retries deliveries and does not guarantee order, so every branch is idempotent.
    """
    event_type = event.get("type", "")
    obj: dict[str, Any] = event.get("data", {}).get("object", {})

    if event_type in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
        return _record_checkout(obj)
    if event_type == "charge.refunded":
        return _record_refund(obj)
    return "ignored"


def _record_checkout(session: dict[str, Any]) -> str:
    if session.get("payment_status") != "paid":
        return "not_paid"
    raw_event_id = str((session.get("metadata") or {}).get(METADATA_KEY, ""))
    if not raw_event_id.isdigit():
        return "no_event"
    event = Event.objects.filter(pk=int(raw_event_id)).first()
    if event is None:
        return "unknown_event"

    _, created = Sale.objects.get_or_create(
        stripe_session_id=session["id"],
        defaults={
            "event": event,
            "stripe_payment_intent_id": session.get("payment_intent") or "",
            "amount_cents": session.get("amount_total") or 0,
            "currency": (session.get("currency") or "").lower(),
            "paid_at": datetime.fromtimestamp(session.get("created") or time.time(), tz=UTC),
        },
    )
    return "recorded" if created else "duplicate"


def _record_refund(charge: dict[str, Any]) -> str:
    payment_intent = charge.get("payment_intent") or ""
    if not payment_intent:
        return "no_sale"
    # `amount_refunded` is cumulative on the charge, so setting it is safe to repeat.
    updated = Sale.objects.filter(stripe_payment_intent_id=payment_intent).update(
        refunded_cents=charge.get("amount_refunded") or 0
    )
    return "refunded" if updated else "no_sale"


@dataclass(frozen=True)
class SalesLine:
    id: int
    name: str
    currency: str
    sales_count: int
    net_cents: int


def _summary(id_field: str, name_field: str) -> list[SalesLine]:
    rows = (
        Sale.objects.values(id_field, name_field, "currency")
        .annotate(n=Count("id"), gross=Sum("amount_cents"), refunded=Sum("refunded_cents"))
        .order_by(name_field, "currency")
    )
    return [
        SalesLine(
            id=row[id_field],
            name=row[name_field],
            currency=row["currency"],
            sales_count=row["n"],
            net_cents=row["gross"] - row["refunded"],
        )
        for row in rows
    ]


def sales_by_event() -> list[SalesLine]:
    return _summary("event_id", "event__title")


def sales_by_speaker() -> list[SalesLine]:
    return _summary("event__speaker_id", "event__speaker__name")
