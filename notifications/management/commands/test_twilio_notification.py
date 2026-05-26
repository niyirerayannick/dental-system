from django.core.management.base import BaseCommand

from notifications.services.twilio_service import send_both


class Command(BaseCommand):
    help = "Send a Twilio SMS and WhatsApp test notification."

    def add_arguments(self, parser):
        parser.add_argument("phone", help="Rwanda phone number, e.g. +250780474044")

    def handle(self, *args, **options):
        phone = options["phone"]
        result = send_both(
            phone,
            "Plan Healthcare Clinic test notification. SMS and WhatsApp delivery are configured.",
        )
        self.stdout.write(self.style.SUCCESS(f"SMS: {result['sms']}"))
        self.stdout.write(self.style.SUCCESS(f"WhatsApp: {result['whatsapp']}"))
