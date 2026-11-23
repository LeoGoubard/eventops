import os
import secrets
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import Membership, Role
from apps.contacts.models import Contact
from apps.events.models import Event, Speaker
from apps.events.services import create_event_with_checklist


class Command(BaseCommand):
    help = "Create demo users, speakers, events and contacts (idempotent)."

    def handle(self, *args: object, **options: object) -> None:
        # Never hardcode credentials: take them from the environment, or generate them.
        demo_secret = os.environ.get("DEMO_PASSWORD") or secrets.token_urlsafe(12)
        created_any = False
        for username, role in [("owner", Role.ADMIN), ("organizer", Role.ORGANIZER), ("host", Role.HOST)]:
            user, created = User.objects.get_or_create(username=username, defaults={"is_staff": True})
            if created:
                user.set_password(demo_secret)
                user.save()
                created_any = True
            Membership.objects.update_or_create(user=user, defaults={"role": role})

        speakers = [
            Speaker.objects.get_or_create(name=name, defaults={"topic": topic})[0]
            for name, topic in [
                ("Maya Ortiz", "Laughter yoga for busy professionals"),
                ("Tom Becker", "Personalised songs that lift your mood"),
            ]
        ]
        if not Event.objects.exists():
            now = timezone.now().replace(minute=0, second=0, microsecond=0)
            create_event_with_checklist(
                title="Laugh your way through Monday", speaker=speakers[0], starts_at=now + timedelta(days=3)
            )
            event = create_event_with_checklist(
                title="A song written just for you", speaker=speakers[1], starts_at=now + timedelta(days=10)
            )
            event.checklist.filter(code__in=["roles", "join_link"]).update(done=True)

        for i in range(1, 26):
            Contact.objects.get_or_create(
                email=f"attendee{i}@example.com", defaults={"marketing_consent": i % 3 != 0}
            )
        message = "Demo data ready. Users: owner / organizer / host."
        if created_any and not os.environ.get("DEMO_PASSWORD"):
            message += f" Generated login secret: {demo_secret}"
        self.stdout.write(self.style.SUCCESS(message))
