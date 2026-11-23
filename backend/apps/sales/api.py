import json
import logging

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.accounts.permissions import can_view_sales
from apps.sales.services import (
    InvalidSignature,
    handle_stripe_event,
    sales_by_event,
    sales_by_speaker,
    verify_signature,
)

logger = logging.getLogger(__name__)
router = Router(tags=["sales"])


class SalesLineOut(Schema):
    id: int
    name: str
    currency: str
    sales_count: int
    net_cents: int


class SalesSummaryOut(Schema):
    by_event: list[SalesLineOut]
    by_speaker: list[SalesLineOut]


@router.get("/summary", response=SalesSummaryOut)
def sales_summary(request: HttpRequest) -> SalesSummaryOut:
    """Net revenue (after refunds) per event and per speaker. Hosts do not see revenue."""
    if not can_view_sales(request.user):
        raise HttpError(403, "Only admins and organizers can see sales.")
    return SalesSummaryOut(
        by_event=[SalesLineOut(**vars(line)) for line in sales_by_event()],
        by_speaker=[SalesLineOut(**vars(line)) for line in sales_by_speaker()],
    )


@csrf_exempt
@require_POST
def stripe_webhook(request: HttpRequest) -> HttpResponse:
    """Receives Stripe events. Not behind session auth: the signature is the authentication."""
    secret: str = settings.STRIPE_WEBHOOK_SECRET
    if not secret:
        return JsonResponse({"detail": "Stripe webhook is not configured."}, status=503)
    try:
        verify_signature(request.body, request.headers.get("Stripe-Signature", ""), secret)
    except InvalidSignature as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    try:
        event = json.loads(request.body)
    except ValueError:
        return JsonResponse({"detail": "Body is not valid JSON."}, status=400)

    outcome = handle_stripe_event(event)
    logger.info("stripe event %s (%s): %s", event.get("id"), event.get("type"), outcome)
    return JsonResponse({"outcome": outcome})
