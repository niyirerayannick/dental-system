import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.utils._os import safe_join
from django.views.decorators.http import require_GET


PRIVATE_PREFIXES = ("ask_doctor/attachments/",)


def _is_private_media(path):
    normalized = path.replace("\\", "/")
    return any(normalized.startswith(prefix) for prefix in PRIVATE_PREFIXES)


def _user_can_access_ask_doctor_attachment(user, path):
    if not user.is_authenticated:
        return False
    if user.is_superuser or getattr(user, "role", None) == "ADMIN":
        return True

    from accounts.models import User
    from ask_doctor.models import DoctorMessage

    message = (
        DoctorMessage.objects.select_related("conversation", "conversation__patient", "conversation__assigned_doctor")
        .filter(attachment=path)
        .first()
    )
    if not message:
        return False

    conversation = message.conversation
    if message.sender_id == user.pk or conversation.patient_id == user.pk:
        return True
    if user.role == User.Role.DENTIST:
        return conversation.assigned_doctor_id in (None, user.pk)
    return False


def _can_access_private_media(user, path):
    normalized = path.replace("\\", "/")
    if normalized.startswith("ask_doctor/attachments/"):
        return _user_can_access_ask_doctor_attachment(user, normalized)
    return False


@require_GET
def serve_media(request, path):
    if not getattr(settings, "SERVE_MEDIA", False):
        raise Http404("Media serving is disabled.")

    normalized_path = path.replace("\\", "/").lstrip("/")
    if _is_private_media(normalized_path) and not _can_access_private_media(request.user, normalized_path):
        return HttpResponseForbidden("You do not have permission to access this file.")

    try:
        full_path = Path(safe_join(settings.MEDIA_ROOT, normalized_path))
    except ValueError as exc:
        raise Http404("Invalid media path.") from exc

    if not full_path.is_file():
        raise Http404("Media file not found.")

    content_type, _ = mimetypes.guess_type(full_path.name)
    return FileResponse(full_path.open("rb"), content_type=content_type or "application/octet-stream")
