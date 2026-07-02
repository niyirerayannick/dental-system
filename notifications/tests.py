from unittest.mock import patch

from django.test import Client, TestCase, override_settings

from notifications.models import NotificationLog
from notifications.services.twilio_service import send_preferred


class TwilioStatusCallbackTests(TestCase):
    @override_settings(TWILIO_VALIDATE_SIGNATURE=False)
    def test_whatsapp_undelivered_sends_sms_fallback_once(self):
        whatsapp_log = NotificationLog.objects.create(
            channel=NotificationLog.Channel.WHATSAPP,
            phone_number="+250780474044",
            message="Muraho, test message.",
            status=NotificationLog.Status.SENT,
            provider_sid="SMWHATSAPP123",
        )

        def fake_send_sms(phone, message, patient=None, appointment=None, parent_log=None):
            fallback_log = NotificationLog.objects.create(
                channel=NotificationLog.Channel.SMS,
                phone_number=phone,
                message=message,
                status=NotificationLog.Status.SENT,
                provider_sid="SMSFALLBACK123",
                patient=patient,
                appointment=appointment,
                parent_log=parent_log,
            )
            return {"ok": True, "status": "sent", "sid": fallback_log.provider_sid, "log_id": fallback_log.pk}

        client = Client()
        payload = {
            "MessageSid": "SMWHATSAPP123",
            "MessageStatus": "undelivered",
            "ErrorCode": "63016",
            "ErrorMessage": "WhatsApp delivery failed.",
        }

        with patch("notifications.services.twilio_service.send_sms", side_effect=fake_send_sms) as mocked_send_sms:
            response = client.post("/api/twilio/status-callback/", data=payload)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(mocked_send_sms.call_count, 1)

            response = client.post("/api/twilio/status-callback/", data=payload)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(mocked_send_sms.call_count, 1)

        whatsapp_log.refresh_from_db()
        self.assertEqual(whatsapp_log.status, NotificationLog.Status.UNDELIVERED)
        self.assertTrue(whatsapp_log.fallback_sent)
        self.assertIsNotNone(whatsapp_log.fallback_log)
        self.assertEqual(whatsapp_log.fallback_log.parent_log, whatsapp_log)
        self.assertEqual(NotificationLog.objects.filter(parent_log=whatsapp_log).count(), 1)

    @override_settings(TWILIO_VALIDATE_SIGNATURE=False)
    def test_delivered_callback_updates_log_without_fallback(self):
        NotificationLog.objects.create(
            channel=NotificationLog.Channel.WHATSAPP,
            phone_number="+250780474044",
            message="Muraho, test message.",
            status=NotificationLog.Status.SENT,
            provider_sid="SMDELIVERED123",
        )

        with patch("notifications.services.twilio_service.send_sms") as mocked_send_sms:
            response = Client().post(
                "/api/twilio/status-callback/",
                data={"MessageSid": "SMDELIVERED123", "MessageStatus": "delivered"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(mocked_send_sms.called)
        log = NotificationLog.objects.get(provider_sid="SMDELIVERED123")
        self.assertEqual(log.status, NotificationLog.Status.DELIVERED)


class PreferredChannelTests(TestCase):
    @override_settings(NOTIFICATION_PREFERRED_CHANNEL="sms")
    @patch("notifications.services.twilio_service.send_whatsapp")
    @patch("notifications.services.twilio_service.send_sms")
    def test_send_preferred_uses_sms_first_by_default(self, mocked_send_sms, mocked_send_whatsapp):
        mocked_send_sms.return_value = {"ok": True, "status": "sent", "log_id": 1}

        result = send_preferred("+250780474044", "Test message")

        self.assertEqual(result["channel"], NotificationLog.Channel.SMS)
        mocked_send_sms.assert_called_once()
        mocked_send_whatsapp.assert_not_called()

    @override_settings(NOTIFICATION_PREFERRED_CHANNEL="sms")
    @patch("notifications.services.twilio_service.send_whatsapp")
    @patch("notifications.services.twilio_service.send_sms")
    def test_send_preferred_falls_back_to_whatsapp_if_sms_api_fails(self, mocked_send_sms, mocked_send_whatsapp):
        mocked_send_sms.return_value = {"ok": False, "status": "failed", "error": "SMS failed", "log_id": 1}
        mocked_send_whatsapp.return_value = {"ok": True, "status": "sent", "log_id": 2}

        result = send_preferred("+250780474044", "Test message")

        self.assertEqual(result["channel"], NotificationLog.Channel.WHATSAPP)
        mocked_send_sms.assert_called_once()
        mocked_send_whatsapp.assert_called_once()
