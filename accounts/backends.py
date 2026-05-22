from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from .models import normalize_phone


class EmailOrPhoneBackend(ModelBackend):
    """Authenticate by email (case-insensitive) or Rwanda phone number."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            return None

        User = get_user_model()
        identifier = username.strip()
        user = None

        if "@" in identifier:
            try:
                user = User.objects.get(email__iexact=identifier)
            except User.DoesNotExist:
                pass
        else:
            normalized = normalize_phone(identifier)
            try:
                user = User.objects.get(phone=normalized)
            except User.DoesNotExist:
                pass

        if user is not None and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
