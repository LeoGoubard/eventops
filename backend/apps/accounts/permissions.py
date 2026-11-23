from django.contrib.auth.models import AbstractBaseUser, AnonymousUser

from apps.accounts.models import Membership, Role


def get_role(user: AbstractBaseUser | AnonymousUser) -> Role | None:
    if not user.is_authenticated:
        return None
    if getattr(user, "is_superuser", False):
        return Role.ADMIN
    membership = Membership.objects.filter(user_id=user.pk).first()
    return Role(membership.role) if membership else None


def can_manage_events(user: AbstractBaseUser | AnonymousUser) -> bool:
    return get_role(user) in {Role.ADMIN, Role.ORGANIZER}


def can_export_contacts(user: AbstractBaseUser | AnonymousUser) -> bool:
    """Only admins can export the mailing list. Everyone else can only use it to send emails."""
    return get_role(user) == Role.ADMIN
