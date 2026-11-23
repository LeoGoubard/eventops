from datetime import UTC, datetime

import pytest
from django.contrib.auth.models import User
from django.test import Client

from apps.accounts.models import Membership, Role
from apps.events.models import Speaker


def _user(username: str, role: Role) -> User:
    user = User.objects.create_user(username=username)
    Membership.objects.create(user=user, role=role)
    return user


@pytest.fixture
def admin_user(db: None) -> User:
    return _user("owner", Role.ADMIN)


@pytest.fixture
def host_user(db: None) -> User:
    return _user("host", Role.HOST)


@pytest.fixture
def organizer_user(db: None) -> User:
    return _user("organizer", Role.ORGANIZER)


@pytest.fixture
def speaker(db: None) -> Speaker:
    return Speaker.objects.create(name="Ada Lovelace", topic="Laughter yoga")


@pytest.fixture
def starts_at() -> datetime:
    return datetime(2027, 1, 5, 19, 0, tzinfo=UTC)


def logged_in(user: User) -> Client:
    client = Client()
    client.force_login(user)
    return client
