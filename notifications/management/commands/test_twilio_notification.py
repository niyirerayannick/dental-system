from django.conf import settings
from django.db import DatabaseError
from django.core.management.base import BaseCommand, CommandError

from notifications.models import NotificationLog
from notifications.services.twilio_service import send_both
from notifications.services.twilio_service import normalize_rwanda_phone


class Command(BaseCommand):
    help = "Send a Twilio SMS and WhatsApp test notification."

    def add_arguments(self, parser):
        parser.add_argument("phone", help="Rwanda phone number, e.g. +250780474044")
        parser.add_argument(
            "--with-log",
            action="store_true",
            help="Use the normal notification service and create NotificationLog records.",
        )

    def handle(self, *args, **options):
        phone = options["phone"]
        message = "Plan Healthcare Clinic test notification. SMS and WhatsApp delivery are configured."

        if options["with_log"]:
            result = send_both(phone, message)
            self._write_result("SMS", result["sms"])
            self._write_result("WhatsApp", result["whatsapp"])
            return

        missing = self._missing_settings()
        if missing:
            raise CommandError("Missing Twilio configuration: " + ", ".join(missing))

        normalized_phone = normalize_rwanda_phone(phone)
        sms_result = self._send_channel(
            channel=NotificationLog.Channel.SMS,
            to=normalized_phone,
            from_=settings.TWILIO_SMS_FROM,
            body=message,
        )
        whatsapp_result = self._send_channel(
            channel=NotificationLog.Channel.WHATSAPP,
            to=f"whatsapp:{normalized_phone}",
            from_=settings.TWILIO_WHATSAPP_FROM,
            body=message,
        )

        self._write_result("SMS", sms_result)
        self._write_result("WhatsApp", whatsapp_result)

    def _missing_settings(self):
        missing = []
        for name in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_SMS_FROM", "TWILIO_WHATSAPP_FROM"):
            if not getattr(settings, name, ""):
                missing.append(name)
        return missing

    def _send_channel(self, channel, to, from_, body):
        from twilio.rest import Client
        from twilio.base.exceptions import TwilioRestException

        log = self._create_log(channel=channel, phone_number=to, message=body)
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        try:
            message = client.messages.create(body=body, from_=from_, to=to)
        except TwilioRestException as exc:
            error = self._twilio_error_message(exc)
            self._save_log_failure(log, error, exc)
            return {"ok": False, "status": "failed", "error": error, "code": getattr(exc, "code", None)}

        result = {
            "ok": True,
            "sid": getattr(message, "sid", ""),
            "status": str(getattr(message, "status", "")),
            "channel": channel,
        }
        self._save_log_success(log, result)
        return result

    def _create_log(self, channel, phone_number, message):
        try:
            return NotificationLog.objects.create(
                channel=channel,
                phone_number=phone_number,
                message=message,
                status=NotificationLog.Status.PENDING,
            )
        except DatabaseError as exc:
            self.stdout.write(self.style.WARNING(f"Could not create NotificationLog: {exc}"))
            return None

    def _save_log_success(self, log, result):
        if not log:
            return
        log.status = NotificationLog.Status.SENT
        log.provider_sid = result["sid"]
        log.response_data = result
        log.error_message = ""
        log.save(update_fields=["status", "provider_sid", "response_data", "error_message", "updated_at"])

    def _save_log_failure(self, log, error, exc):
        if not log:
            return
        log.status = NotificationLog.Status.FAILED
        log.error_message = error
        log.response_data = {
            "exception": exc.__class__.__name__,
            "code": getattr(exc, "code", None),
            "status": getattr(exc, "status", None),
            "uri": getattr(exc, "uri", ""),
        }
        log.save(update_fields=["status", "error_message", "response_data", "updated_at"])

    def _twilio_error_message(self, exc):
        code = getattr(exc, "code", None) or "unknown"
        message = getattr(exc, "msg", "") or str(exc)
        return f"Twilio error {code}: {message}"

    def _write_result(self, label, result):
        if result.get("ok"):
            sid = result.get("sid", "")
            suffix = f" (SID: {sid})" if sid else ""
            self.stdout.write(self.style.SUCCESS(f"{label}: sent successfully{suffix}"))
            return
        self.stdout.write(self.style.ERROR(f"{label}: failed - {result.get('error', 'Unknown error')}"))
