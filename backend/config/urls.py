from django.contrib import admin
from django.http import HttpRequest, JsonResponse
from django.urls import path

from config.api import api


def healthz(_request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
    path("healthz", healthz),
]
