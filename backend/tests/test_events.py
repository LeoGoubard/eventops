import json
from datetime import datetime

from django.contrib.auth.models import User

from apps.events.models import Speaker
from apps.events.services import DEFAULT_CHECKLIST, create_event_with_checklist, readiness
from tests.conftest import logged_in


def test_new_event_gets_default_checklist(speaker: Speaker, starts_at: datetime) -> None:
    event = create_event_with_checklist(title="Intro", speaker=speaker, starts_at=starts_at)

    codes = list(event.checklist.values_list("code", flat=True))
    assert codes == [code for code, _ in DEFAULT_CHECKLIST]
    r = readiness(event)
    assert (r.done, r.percent, r.is_ready) == (0, 0, False)


def test_event_is_ready_only_when_every_item_is_done(speaker: Speaker, starts_at: datetime) -> None:
    event = create_event_with_checklist(title="Intro", speaker=speaker, starts_at=starts_at)
    event.checklist.exclude(code="roles").update(done=True)
    assert readiness(event).is_ready is False

    event.checklist.filter(code="roles").update(done=True)
    assert readiness(event).is_ready is True
    assert readiness(event).percent == 100


def test_organizer_can_create_event_via_api(
    organizer_user: User, speaker: Speaker, starts_at: datetime
) -> None:
    client = logged_in(organizer_user)
    response = client.post(
        "/api/events/",
        data=json.dumps(
            {"title": "Laughter yoga", "speaker_id": speaker.id, "starts_at": starts_at.isoformat()}
        ),
        content_type="application/json",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["readiness_percent"] == 0
    assert len(body["checklist"]) == len(DEFAULT_CHECKLIST)


def test_host_cannot_create_event(host_user: User, speaker: Speaker, starts_at: datetime) -> None:
    client = logged_in(host_user)
    response = client.post(
        "/api/events/",
        data=json.dumps({"title": "x", "speaker_id": speaker.id, "starts_at": starts_at.isoformat()}),
        content_type="application/json",
    )
    assert response.status_code == 403


def test_host_can_tick_checklist(host_user: User, speaker: Speaker, starts_at: datetime) -> None:
    event = create_event_with_checklist(title="Intro", speaker=speaker, starts_at=starts_at)
    item = event.checklist.get(code="join_link")
    client = logged_in(host_user)

    response = client.patch(
        f"/api/events/{event.id}/checklist/{item.id}",
        data=json.dumps({"done": True}),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["readiness_percent"] == round(100 / len(DEFAULT_CHECKLIST))


def test_api_requires_login(db: None) -> None:
    from django.test import Client

    assert Client().get("/api/events/").status_code == 401
