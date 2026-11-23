from django.http import HttpRequest
from ninja import NinjaAPI
from ninja.security import django_auth

from apps.accounts.permissions import get_role
from apps.contacts.api import router as contacts_router
from apps.events.api import router as events_router

api = NinjaAPI(
    title="EventOps API",
    version="0.1.0",
    description="Events, speakers, pre-live checklists and contacts for online event organisers.",
    auth=django_auth,
)

api.add_router("/events", events_router)
api.add_router("/contacts", contacts_router)


@api.get("/me", tags=["auth"])
def me(request: HttpRequest) -> dict[str, str | None]:
    role = get_role(request.user)
    return {"username": request.user.get_username(), "role": role.value if role else None}
