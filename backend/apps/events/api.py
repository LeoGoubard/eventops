from datetime import datetime

from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.accounts.permissions import can_manage_events
from apps.events.models import ChecklistItem, Event, Speaker
from apps.events.services import create_event_with_checklist, readiness

router = Router(tags=["events"])


class ChecklistItemOut(Schema):
    id: int
    code: str
    label: str
    done: bool


class EventIn(Schema):
    title: str
    speaker_id: int
    starts_at: datetime
    duration_minutes: int = 60
    join_url: str = ""
    offer_url: str = ""


class EventOut(Schema):
    id: int
    title: str
    speaker: str
    starts_at: datetime
    duration_minutes: int
    status: str
    join_url: str
    offer_url: str
    readiness_percent: int
    is_ready: bool
    checklist: list[ChecklistItemOut]


class ChecklistToggleIn(Schema):
    done: bool


def _to_out(event: Event) -> EventOut:
    r = readiness(event)
    return EventOut(
        id=event.id,
        title=event.title,
        speaker=event.speaker.name,
        starts_at=event.starts_at,
        duration_minutes=event.duration_minutes,
        status=event.status,
        join_url=event.join_url,
        offer_url=event.offer_url,
        readiness_percent=r.percent,
        is_ready=r.is_ready,
        checklist=[
            ChecklistItemOut(id=i.id, code=i.code, label=i.label, done=i.done) for i in event.checklist.all()
        ],
    )


@router.get("/", response=list[EventOut])
def list_events(request: HttpRequest) -> list[EventOut]:
    events = Event.objects.select_related("speaker").prefetch_related("checklist")
    return [_to_out(e) for e in events]


@router.post("/", response={201: EventOut})
def create_event(request: HttpRequest, payload: EventIn) -> tuple[int, EventOut]:
    if not can_manage_events(request.user):
        raise HttpError(403, "Only admins and organizers can create events.")
    speaker = get_object_or_404(Speaker, pk=payload.speaker_id)
    event = create_event_with_checklist(
        title=payload.title,
        speaker=speaker,
        starts_at=payload.starts_at,
        duration_minutes=payload.duration_minutes,
        join_url=payload.join_url,
        offer_url=payload.offer_url,
    )
    return 201, _to_out(event)


@router.patch("/{event_id}/checklist/{item_id}", response=EventOut)
def toggle_checklist_item(
    request: HttpRequest, event_id: int, item_id: int, payload: ChecklistToggleIn
) -> EventOut:
    item = get_object_or_404(ChecklistItem, pk=item_id, event_id=event_id)
    item.done = payload.done
    item.save(update_fields=["done"])
    event = Event.objects.select_related("speaker").prefetch_related("checklist").get(pk=event_id)
    return _to_out(event)
