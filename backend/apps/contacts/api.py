import csv
import io

from django.http import HttpRequest, HttpResponse
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.accounts.permissions import can_export_contacts
from apps.contacts.models import Contact

router = Router(tags=["contacts"])


class ContactStats(Schema):
    total: int
    with_consent: int


@router.get("/stats", response=ContactStats)
def contact_stats(request: HttpRequest) -> ContactStats:
    """Any team member can see list size, which is enough to plan a campaign."""
    return ContactStats(
        total=Contact.objects.count(),
        with_consent=Contact.objects.filter(marketing_consent=True).count(),
    )


@router.get("/export.csv")
def export_contacts(request: HttpRequest) -> HttpResponse:
    """Export the full list as CSV. Restricted to admins: the list is the business's main asset."""
    if not can_export_contacts(request.user):
        raise HttpError(403, "Only admins can export the contact list.")
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["email", "first_name", "marketing_consent"])
    for c in Contact.objects.all().iterator():
        writer.writerow([c.email, c.first_name, c.marketing_consent])
    response = HttpResponse(buffer.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="contacts.csv"'
    return response
