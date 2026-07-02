import logging
import re

from django.conf import settings
from django.db import transaction

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


FINAL_FAILURE_STATUSES = {
    NotificationLog.Status.FAILED,
    NotificationLog.Status.UNDELIVERED,
}

TWILIO_STATUS_MAP = {
    "accepted": NotificationLog.Status.QUEUED,
    "queued": NotificationLog.Status.QUEUED,
    "sending": NotificationLog.Status.QUEUED,
    "sent": NotificationLog.Status.SENT,
    "delivered": NotificationLog.Status.DELIVERED,
    "read": NotificationLog.Status.DELIVERED,
    "failed": NotificationLog.Status.FAILED,
    "undelivered": NotificationLog.Status.UNDELIVERED,
}


def _send(channel, phone, message, patient=None, appointment=None, parent_log=None):
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
            parent_log=parent_log,
        )
        return {"ok": False, "status": "failed", "error": str(exc), "log_id": log.pk}

    log = NotificationLog.objects.create(
        patient=patient,
        appointment=appointment,
        channel=channel,
        phone_number=normalized_phone,
        message=message,
        status=NotificationLog.Status.PENDING,
        parent_log=parent_log,
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

        send_kwargs = {
            "body": message,
            "from_": from_number,
            "to": to_number,
        }
        if settings.TWILIO_STATUS_CALLBACK_URL:
            send_kwargs["status_callback"] = settings.TWILIO_STATUS_CALLBACK_URL

        twilio_message = client.messages.create(**send_kwargs)
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


def send_sms(phone, message, patient=None, appointment=None, parent_log=None):
    return _send(NotificationLog.Channel.SMS, phone, message, patient=patient, appointment=appointment, parent_log=parent_log)


def send_whatsapp(phone, message, patient=None, appointment=None, parent_log=None):
    return _send(NotificationLog.Channel.WHATSAPP, phone, message, patient=patient, appointment=appointment, parent_log=parent_log)


def send_preferred(phone, message, patient=None, appointment=None):
    preferred_channel = getattr(settings, "NOTIFICATION_PREFERRED_CHANNEL", "sms")

    if preferred_channel == NotificationLog.Channel.WHATSAPP:
        whatsapp_result = send_whatsapp(phone, message, patient=patient, appointment=appointment)
        if whatsapp_result.get("ok"):
            return {
                "ok": True,
                "channel": NotificationLog.Channel.WHATSAPP,
                "result": whatsapp_result,
                "whatsapp": whatsapp_result,
                "sms": None,
            }

        sms_result = send_sms(phone, message, patient=patient, appointment=appointment)
        return {
            "ok": sms_result.get("ok", False),
            "channel": NotificationLog.Channel.SMS if sms_result.get("ok") else None,
            "result": sms_result,
            "whatsapp": whatsapp_result,
            "sms": sms_result,
        }

    sms_result = send_sms(phone, message, patient=patient, appointment=appointment)
    if sms_result.get("ok"):
        return {
            "ok": True,
            "channel": NotificationLog.Channel.SMS,
            "result": sms_result,
            "whatsapp": None,
            "sms": sms_result,
        }

    whatsapp_result = send_whatsapp(phone, message, patient=patient, appointment=appointment)
    return {
        "ok": whatsapp_result.get("ok", False),
        "channel": NotificationLog.Channel.WHATSAPP if whatsapp_result.get("ok") else None,
        "result": whatsapp_result,
        "whatsapp": whatsapp_result,
        "sms": sms_result,
    }


def sync_twilio_log_status(log):
    if not log.provider_sid:
        return {"ok": False, "error": "NotificationLog has no provider SID.", "log_id": log.pk}
    if _missing_credentials(log.channel):
        return {"ok": False, "error": "Missing Twilio credentials.", "log_id": log.pk}

    from twilio.rest import Client

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    message = client.messages(log.provider_sid).fetch()
    status = normalize_twilio_status(getattr(message, "status", ""))
    error_code = getattr(message, "error_code", None) or ""
    error_message = getattr(message, "error_message", None) or ""
    response_data = dict(log.response_data or {})
    response_data.update(
        {
            "synced_status": getattr(message, "status", ""),
            "synced_error_code": error_code,
            "synced_error_message": error_message,
        }
    )
    log.status = status
    log.response_data = response_data
    if error_code or error_message:
        log.error_message = " ".join(str(part) for part in (error_code, error_message) if part)
    elif status not in FINAL_FAILURE_STATUSES:
        log.error_message = ""
    log.save(update_fields=["status", "response_data", "error_message", "updated_at"])
    return {
        "ok": True,
        "log_id": log.pk,
        "status": status,
        "twilio_status": getattr(message, "status", ""),
        "error_code": error_code,
        "error_message": error_message,
    }
def send_both(phone, message, patient=None, appointment=None):
    return {
        "sms": send_sms(phone, message, patient=patient, appointment=appointment),
        "whatsapp": send_whatsapp(phone, message, patient=patient, appointment=appointment),
    }


def normalize_twilio_status(status):
    return TWILIO_STATUS_MAP.get(str(status or "").strip().lower(), NotificationLog.Status.PENDING)


def handle_status_callback(payload):
    provider_sid = payload.get("MessageSid") or payload.get("SmsSid") or payload.get("SmsMessageSid")
    if not provider_sid:
        return {"ok": False, "error": "Missing MessageSid."}

    with transaction.atomic():
        log = (
            NotificationLog.objects.select_for_update()
            .select_related("patient", "appointment", "fallback_log", "parent_log")
            .filter(provider_sid=provider_sid)
            .first()
        )
        if not log:
            return {"ok": False, "error": "NotificationLog not found.", "sid": provider_sid}

        raw_status = payload.get("MessageStatus") or payload.get("SmsStatus") or payload.get("MessageStatusCallback")
        status = normalize_twilio_status(raw_status)
        error_code = payload.get("ErrorCode") or ""
        error_message = payload.get("ErrorMessage") or ""
        response_data = dict(log.response_data or {})
        response_data.update(
            {
                "callback_status": raw_status,
                "callback_error_code": error_code,
                "callback_error_message": error_message,
                "callback_to": payload.get("To", ""),
                "callback_from": payload.get("From", ""),
            }
        )

        log.status = status
        log.response_data = response_data
        if error_code or error_message:
            log.error_message = " ".join(part for part in (error_code, error_message) if part)
        elif status not in FINAL_FAILURE_STATUSES:
            log.error_message = ""

        fallback_result = None
        should_fallback = (
            log.channel == NotificationLog.Channel.WHATSAPP
            and status in FINAL_FAILURE_STATUSES
            and not log.fallback_sent
            and not log.fallback_log_id
            and not log.fallback_attempts.exists()
        )
        if should_fallback:
            log.fallback_sent = True
            log.save(update_fields=["status", "response_data", "error_message", "fallback_sent", "updated_at"])
            fallback_result = send_sms(
                log.phone_number,
                log.message,
                patient=log.patient,
                appointment=log.appointment,
                parent_log=log,
            )
            fallback_log_id = fallback_result.get("log_id")
            if fallback_log_id:
                log.fallback_log_id = fallback_log_id
                log.save(update_fields=["fallback_log", "updated_at"])
        else:
            log.save(update_fields=["status", "response_data", "error_message", "updated_at"])

    return {"ok": True, "log_id": log.pk, "status": status, "fallback": fallback_result}
