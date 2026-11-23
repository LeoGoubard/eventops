from django.contrib.auth.models import User

from apps.contacts.models import Contact
from tests.conftest import logged_in


def _seed() -> None:
    Contact.objects.create(email="a@example.com", first_name="Ana", marketing_consent=True)
    Contact.objects.create(email="b@example.com", first_name="Ben", marketing_consent=False)


def test_admin_can_export_contacts(admin_user: User) -> None:
    _seed()
    response = logged_in(admin_user).get("/api/contacts/export.csv")
    assert response.status_code == 200
    lines = response.content.decode().strip().splitlines()
    assert lines[0] == "email,first_name,marketing_consent"
    assert len(lines) == 3


def test_host_cannot_export_contacts(host_user: User) -> None:
    _seed()
    response = logged_in(host_user).get("/api/contacts/export.csv")
    assert response.status_code == 403


def test_any_member_sees_list_size(host_user: User) -> None:
    _seed()
    body = logged_in(host_user).get("/api/contacts/stats").json()
    assert body == {"total": 2, "with_consent": 1}
