"""Business rules for events.

The pre-live checklist exists because the most common webinar failures are boring ones:
host and presenter roles swapped, a broken join link, a wrong date in the invitation.
"""

from dataclasses import dataclass

from django.db import transaction

from apps.events.models import ChecklistItem, Event

DEFAULT_CHECKLIST: list[tuple[str, str]] = [
    ("roles", "Host and presenter roles are set correctly on the webinar platform"),
    ("join_link", "Join link opens the right session"),
    ("date_time", "Date and time are correct in every invitation and reminder"),
    ("emails_formatting", "Invitation and reminder emails render correctly (no stray bold or italics)"),
    ("speaker_briefed", "Speaker has the link, the run-of-show and a test call"),
    ("replay_offer", "Replay email and offer page are ready for the next morning"),
]


@transaction.atomic
def create_event_with_checklist(**fields: object) -> Event:
    event = Event.objects.create(**fields)
    ChecklistItem.objects.bulk_create(
        ChecklistItem(event=event, code=code, label=label, position=i)
        for i, (code, label) in enumerate(DEFAULT_CHECKLIST)
    )
    return event


@dataclass(frozen=True)
class Readiness:
    done: int
    total: int

    @property
    def percent(self) -> int:
        return round(100 * self.done / self.total) if self.total else 0

    @property
    def is_ready(self) -> bool:
        return self.total > 0 and self.done == self.total


def readiness(event: Event) -> Readiness:
    items = list(event.checklist.all())
    return Readiness(done=sum(1 for i in items if i.done), total=len(items))
