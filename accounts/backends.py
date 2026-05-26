from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from .models import normalize_phone


class EmailOrPhoneBackend(ModelBackend):
    """Authenticate by email (case-insensitive) or Rwanda phone number."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        identifier = username or kwargs.get(User.USERNAME_FIELD) or kwargs.get("phone") or kwargs.get("email")
        if identifier is None or password is None:
            return None

        identifier = str(identifier).strip()
        if not identifier:
            return None

        if "@" in identifier:
            identifier = User.objects.normalize_email(identifier).lower()
            user = User.objects.filter(email__iexact=identifier).first()
        else:
            normalized = normalize_phone(identifier)
            user = User.objects.filter(phone=normalized).first()

        if user is not None and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
