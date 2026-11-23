import hashlib
import hmac
import json
import time
from datetime import datetime
from typing import Any

import pytest
from django.contrib.auth.models import User
from django.test import Client
from pytest_django.fixtures import Settings as SettingsWrapper

from apps.events.models import Event, Speaker
from apps.events.services import create_event_with_checklist
from apps.sales.models import Sale
from apps.sales.services import InvalidSignature, verify_signature
from tests.conftest import logged_in

SIGNING_KEY = "whsec_" + "x" * 24  # throwaway value, only used to sign test payloads


@pytest.fixture(autouse=True)
def _webhook_configured(settings: SettingsWrapper) -> None:
    settings.STRIPE_WEBHOOK_SECRET = SIGNING_KEY


@pytest.fixture
def event(speaker: Speaker, starts_at: datetime) -> Event:
    return create_event_with_checklist(title="Laughter yoga", speaker=speaker, starts_at=starts_at)


def _sign(body: bytes, key: str = SIGNING_KEY, timestamp: int | None = None) -> str:
    t = int(time.time()) if timestamp is None else timestamp
    digest = hmac.new(key.encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={t},v1={digest}"


def _deliver(payload: dict[str, Any], signature: str | None = None) -> Any:
    body = json.dumps(payload).encode()
    return Client().post(
        "/api/stripe/webhook",
        data=body,
        content_type="application/json",
        headers={"Stripe-Signature": _sign(body) if signature is None else signature},
    )


def _checkout(event_id: int | str, session_id: str = "cs_test_1", amount: int = 9700) -> dict[str, Any]:
    return {
        "id": f"evt_{session_id}",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": session_id,
                "payment_status": "paid",
                "payment_intent": f"pi_{session_id}",
                "amount_total": amount,
                "currency": "eur",
                "created": 1798830000,
                "metadata": {"eventops_event_id": str(event_id)},
            }
        },
    }


def _refund(session_id: str, amount_refunded: int) -> dict[str, Any]:
    return {
        "id": "evt_refund",
        "type": "charge.refunded",
        "data": {"object": {"payment_intent": f"pi_{session_id}", "amount_refunded": amount_refunded}},
    }


def test_paid_checkout_is_recorded_against_its_event(event: Event) -> None:
    response = _deliver(_checkout(event.id))

    assert response.status_code == 200
    assert response.json() == {"outcome": "recorded"}
    sale = Sale.objects.get()
    assert (sale.event_id, sale.amount_cents, sale.currency) == (event.id, 9700, "eur")


def test_stripe_retries_do_not_create_duplicates(event: Event) -> None:
    _deliver(_checkout(event.id))
    response = _deliver(_checkout(event.id))

    assert response.json() == {"outcome": "duplicate"}
    assert Sale.objects.count() == 1


def test_wrong_signature_is_rejected(event: Event) -> None:
    body = json.dumps(_checkout(event.id)).encode()
    response = _deliver(_checkout(event.id), signature=_sign(body, key="whsec_someone_else"))

    assert response.status_code == 400
    assert Sale.objects.count() == 0


def test_replayed_old_delivery_is_rejected() -> None:
    body = b"{}"
    old = int(time.time()) - 3600
    with pytest.raises(InvalidSignature):
        verify_signature(body, _sign(body, timestamp=old), SIGNING_KEY)


def test_endpoint_is_disabled_without_a_signing_secret(event: Event, settings: SettingsWrapper) -> None:
    settings.STRIPE_WEBHOOK_SECRET = ""
    assert _deliver(_checkout(event.id)).status_code == 503


@pytest.mark.parametrize(
    ("mutate", "outcome"),
    [
        (lambda s: s.update(payment_status="unpaid"), "not_paid"),
        (lambda s: s.update(metadata={}), "no_event"),
        (lambda s: s.update(metadata={"eventops_event_id": "999999"}), "unknown_event"),
    ],
)
def test_checkouts_that_cannot_be_attributed_are_skipped(event: Event, mutate: Any, outcome: str) -> None:
    payload = _checkout(event.id)
    mutate(payload["data"]["object"])

    assert _deliver(payload).json() == {"outcome": outcome}
    assert Sale.objects.count() == 0


def test_refund_lowers_net_revenue(event: Event, organizer_user: User) -> None:
    _deliver(_checkout(event.id, "cs_test_1", amount=9700))
    _deliver(_checkout(event.id, "cs_test_2", amount=9700))
    _deliver(_refund("cs_test_1", 9700))
    _deliver(_refund("cs_test_1", 9700))  # retried delivery

    body = logged_in(organizer_user).get("/api/sales/summary").json()
    assert body["by_event"] == [
        {"id": event.id, "name": "Laughter yoga", "currency": "eur", "sales_count": 2, "net_cents": 9700}
    ]
    assert body["by_speaker"][0]["name"] == "Ada Lovelace"
    assert body["by_speaker"][0]["net_cents"] == 9700


def test_speaker_total_adds_up_across_events(event: Event, starts_at: datetime, admin_user: User) -> None:
    second = create_event_with_checklist(title="Round two", speaker=event.speaker, starts_at=starts_at)
    _deliver(_checkout(event.id, "cs_test_1", amount=5000))
    _deliver(_checkout(second.id, "cs_test_2", amount=7000))

    body = logged_in(admin_user).get("/api/sales/summary").json()
    assert len(body["by_event"]) == 2
    assert [(s["sales_count"], s["net_cents"]) for s in body["by_speaker"]] == [(2, 12000)]


def test_host_cannot_see_sales(host_user: User) -> None:
    assert logged_in(host_user).get("/api/sales/summary").status_code == 403
