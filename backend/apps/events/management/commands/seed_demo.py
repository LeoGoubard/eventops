import os
import secrets
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import Membership, Role
from apps.contacts.models import Contact
from apps.events.models import Event, EventStatus, Speaker
from apps.events.services import create_event_with_checklist
from apps.sales.models import Sale


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

        # A past session with sales, so the dashboard shows revenue without a Stripe account.
        if not Event.objects.filter(title="Breathe, laugh, reset").exists():
            past = create_event_with_checklist(
                title="Breathe, laugh, reset",
                speaker=speakers[0],
                starts_at=timezone.now().replace(minute=0, second=0, microsecond=0) - timedelta(days=7),
                status=EventStatus.DONE,
            )
            past.checklist.update(done=True)
            for i, (amount, refunded) in enumerate([(9700, 0), (9700, 0), (9700, 9700), (14700, 0)]):
                Sale.objects.create(
                    event=past,
                    stripe_session_id=f"demo_session_{i}",
                    amount_cents=amount,
                    refunded_cents=refunded,
                    currency="eur",
                    paid_at=past.starts_at + timedelta(days=1, hours=i),
                )

        for i in range(1, 26):
            Contact.objects.get_or_create(
                email=f"attendee{i}@example.com", defaults={"marketing_consent": i % 3 != 0}
            )
        message = "Demo data ready. Users: owner / organizer / host."
        if created_any and not os.environ.get("DEMO_PASSWORD"):
            message += f" Generated login secret: {demo_secret}"
        self.stdout.write(self.style.SUCCESS(message))
