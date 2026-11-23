from django.contrib import admin
from django.http import HttpRequest, JsonResponse
from django.urls import path

from apps.sales.api import stripe_webhook
from config.api import api


def healthz(_request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/stripe/webhook", stripe_webhook),
    path("api/", api.urls),
    path("healthz", healthz),
]
