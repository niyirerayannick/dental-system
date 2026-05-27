import logging
import re

from django.conf import settings

from notifications.models import NotificationLog

logger = logging.getLogger(__name__)


RWANDA_PHONE_RE = re.compile(r"^\+2507\d{8}$")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def normalize_rwanda_phone(phone):
    if not phone:
        raise ValueError("Phone number is required.")

    cleaned = re.sub(r"[\s().-]", "", str(phone).strip())
    if cleaned.lower().startswith("whatsapp:"):
        cleaned = cleaned.split(":", 1)[1]
    digits = cleaned.lstrip("+")

    if digits.startswith("07") and len(digits) == 10:
        normalized = "+250" + digits[1:]
    elif digits.startswith("2507") and len(digits) == 12:
        normalized = "+" + digits
    elif cleaned.startswith("+2507") and len(digits) == 12:
        normalized = cleaned
    else:
        raise ValueError("Use Rwanda phone format +2507XXXXXXXX.")

    if not RWANDA_PHONE_RE.match(normalized):
        raise ValueError("Use Rwanda phone format +2507XXXXXXXX.")
    return normalized


def _clean_response(message):
    return {
        "sid": getattr(message, "sid", ""),
        "status": str(getattr(message, "status", "")),
        "to": str(getattr(message, "to", "")),
        "from": str(getattr(message, "from_", "")),
        "error_code": getattr(message, "error_code", None),
        "error_message": getattr(message, "error_message", None),
    }


def _twilio_error_message(exc):
    code = getattr(exc, "code", None) or "unknown"
    message = getattr(exc, "msg", "") or str(exc)
    message = ANSI_RE.sub("", message).strip()
    return f"Twilio error {code}: {message}"


def _missing_credentials(channel):
    missing = []
    if not settings.TWILIO_ACCOUNT_SID:
        missing.append("TWILIO_ACCOUNT_SID")
    if not settings.TWILIO_AUTH_TOKEN:
        missing.append("TWILIO_AUTH_TOKEN")
    if channel == NotificationLog.Channel.SMS and not settings.TWILIO_SMS_FROM:
        missing.append("TWILIO_SMS_FROM")
    if channel == NotificationLog.Channel.WHATSAPP and not settings.TWILIO_WHATSAPP_FROM:
        missing.append("TWILIO_WHATSAPP_FROM")
    return missing


def _send(channel, phone, message, patient=None, appointment=None):
    log = None
    try:
        normalized_phone = normalize_rwanda_phone(phone)
    except ValueError as exc:
        log = NotificationLog.objects.create(
            patient=patient,
            appointment=appointment,
            channel=channel,
            phone_number=str(phone or ""),
            message=message,
            status=NotificationLog.Status.FAILED,
            error_message=str(exc),
        )
        return {"ok": False, "status": "failed", "error": str(exc), "log_id": log.pk}

    log = NotificationLog.objects.create(
        patient=patient,
        appointment=appointment,
        channel=channel,
        phone_number=normalized_phone,
        message=message,
        status=NotificationLog.Status.PENDING,
    )

    missing = _missing_credentials(channel)
    if missing:
        error = "Missing Twilio configuration: " + ", ".join(missing)
        log.status = NotificationLog.Status.FAILED
        log.error_message = error
        log.save(update_fields=["status", "error_message", "updated_at"])
        return {"ok": False, "status": "failed", "error": error, "log_id": log.pk}

    try:
        from twilio.rest import Client

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        to_number = normalized_phone
        from_number = settings.TWILIO_SMS_FROM

        if channel == NotificationLog.Channel.WHATSAPP:
            to_number = f"whatsapp:{normalized_phone}"
            from_number = settings.TWILIO_WHATSAPP_FROM

        twilio_message = client.messages.create(
            body=message,
            from_=from_number,
            to=to_number,
        )
        response_data = _clean_response(twilio_message)
        log.status = NotificationLog.Status.SENT
        log.provider_sid = response_data["sid"]
        log.response_data = response_data
        log.error_message = ""
        log.save(update_fields=["status", "provider_sid", "response_data", "error_message", "updated_at"])
        return {"ok": True, "status": "sent", "sid": response_data["sid"], "log_id": log.pk}
    except Exception as exc:
        logger.exception("Twilio %s notification failed", channel)
        log.status = NotificationLog.Status.FAILED
        log.error_message = _twilio_error_message(exc)
        log.response_data = {"exception": exc.__class__.__name__}
        log.save(update_fields=["status", "error_message", "response_data", "updated_at"])
        return {"ok": False, "status": "failed", "error": log.error_message, "log_id": log.pk}


def send_sms(phone, message, patient=None, appointment=None):
    return _send(NotificationLog.Channel.SMS, phone, message, patient=patient, appointment=appointment)


def send_whatsapp(phone, message, patient=None, appointment=None):
    return _send(NotificationLog.Channel.WHATSAPP, phone, message, patient=patient, appointment=appointment)


def send_both(phone, message, patient=None, appointment=None):
    return {
        "sms": send_sms(phone, message, patient=patient, appointment=appointment),
        "whatsapp": send_whatsapp(phone, message, patient=patient, appointment=appointment),
    }
