from django.core.management.base import BaseCommand

from notifications.models import NotificationLog
from notifications.services.twilio_service import sync_twilio_log_status


class Command(BaseCommand):
    help = "Fetch current Twilio statuses for recent NotificationLog rows with provider SIDs."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50, help="Number of recent provider-backed logs to sync.")

    def handle(self, *args, **options):
        logs = NotificationLog.objects.exclude(provider_sid="").order_by("-created_at")[: options["limit"]]
        if not logs:
            self.stdout.write("No Twilio provider-backed notification logs found.")
            return

        for log in logs:
            result = sync_twilio_log_status(log)
            if result.get("ok"):
                suffix = ""
                if result.get("error_code") or result.get("error_message"):
                    suffix = f" error={result.get('error_code') or ''} {result.get('error_message') or ''}".rstrip()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Log #{log.pk} {log.channel}: {result['twilio_status']} -> {result['status']}{suffix}"
                    )
                )
            else:
                self.stdout.write(self.style.ERROR(f"Log #{log.pk}: {result.get('error', 'sync failed')}"))
