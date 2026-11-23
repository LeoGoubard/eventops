from django.conf import settings
from django.db import models


class Role(models.TextChoices):
    """What a team member is allowed to do.

    Small event businesses rely on freelance hosts and assistants. They need to prepare
    events and send emails, but only the owner should be able to export the contact list.
    """

    ADMIN = "admin", "Admin"
    ORGANIZER = "organizer", "Organizer"
    HOST = "host", "Host"


class Membership(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="membership")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.HOST)

    def __str__(self) -> str:
        return f"{self.user} ({self.role})"
