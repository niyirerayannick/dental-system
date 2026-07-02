from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Safely check whether Twilio notification settings are loaded."

    def handle(self, *args, **options):
        env_path = Path(settings.BASE_DIR) / ".env"

        self.stdout.write(f"Project root: {settings.BASE_DIR}")
        self.stdout.write(f".env path: {env_path}")
        self.stdout.write(f".env exists: {self._yes_no(env_path.exists())}")
        self.stdout.write("")
        self.stdout.write("Database:")
        self.stdout.write(f"Engine: {settings.DATABASES['default'].get('ENGINE', '')}")
        self.stdout.write(f"Name: {self._masked(settings.DATABASES['default'].get('NAME', ''))}")
        self.stdout.write(f"Host: {settings.DATABASES['default'].get('HOST', '') or '(local sqlite/file)'}")
        self.stdout.write("")
        self.stdout.write(f"SID loaded: {self._yes_no(settings.TWILIO_ACCOUNT_SID)}{self._masked(settings.TWILIO_ACCOUNT_SID)}")
        self.stdout.write(f"Auth token loaded: {self._yes_no(settings.TWILIO_AUTH_TOKEN)}")
        self.stdout.write(f"SMS from loaded: {self._yes_no(settings.TWILIO_SMS_FROM)}{self._masked(settings.TWILIO_SMS_FROM)}")
        self.stdout.write(f"WhatsApp from loaded: {self._yes_no(settings.TWILIO_WHATSAPP_FROM)}{self._masked(settings.TWILIO_WHATSAPP_FROM)}")
        self.stdout.write(f"Status callback URL loaded: {self._yes_no(settings.TWILIO_STATUS_CALLBACK_URL)}")
        self.stdout.write(f"Signature validation: {'enabled' if settings.TWILIO_VALIDATE_SIGNATURE else 'disabled'}")
        self.stdout.write(f"Preferred notification channel: {settings.NOTIFICATION_PREFERRED_CHANNEL}")
        self.stdout.write(f"Clinic name loaded: {self._yes_no(settings.CLINIC_NAME)}")
        self.stdout.write(f"Clinic phone loaded: {self._yes_no(settings.CLINIC_PHONE)}{self._masked(settings.CLINIC_PHONE)}")

    def _yes_no(self, value):
        return "yes" if value else "no"

    def _masked(self, value):
        if not value:
            return ""
        value = str(value)
        if len(value) <= 4:
            return " (****)"
        return f" (...{value[-4:]})"
