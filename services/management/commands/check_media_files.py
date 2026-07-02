import re
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import OperationalError


class Command(BaseCommand):
    help = "Diagnose uploaded media configuration, URLs, and missing files."

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)
        self._print_config(media_root)

        try:
            records = self._media_records()
        except OperationalError as exc:
            self.stdout.write(self.style.ERROR("Could not query media records."))
            self.stdout.write(str(exc))
            return

        service_images = [record for record in records if record["group"] == "services"]
        broken = []

        self.stdout.write("Database counts:")
        self.stdout.write(f"  Service image references in DB: {len(service_images)}")
        self.stdout.write(f"  All uploaded media references in DB: {len(records)}")
        self.stdout.write("")

        self.stdout.write("Sample files:")
        if not records:
            self.stdout.write("  No uploaded media references found.")
        for record in records[:20]:
            exists = self._print_record(record, media_root)
            if not exists:
                broken.append(record)

        for record in records[20:]:
            file_path = media_root / record["name"]
            if not file_path.exists():
                broken.append(record)

        self.stdout.write("")
        self.stdout.write("Broken DB image/file references:")
        if not broken:
            self.stdout.write(self.style.SUCCESS("  None found."))
        else:
            for record in broken:
                self.stdout.write(self.style.ERROR(f"  {record['label']} -> {record['name']}"))

    def _print_config(self, media_root):
        self.stdout.write("Media configuration:")
        self.stdout.write(f"  BASE_DIR: {settings.BASE_DIR}")
        self.stdout.write(f"  MEDIA_ROOT: {media_root}")
        self.stdout.write(f"  MEDIA_URL: {settings.MEDIA_URL}")
        self.stdout.write(f"  MEDIA_ROOT exists: {'yes' if media_root.exists() else 'no'}")
        self.stdout.write(f"  STATIC_URL: {settings.STATIC_URL}")
        self.stdout.write(f"  STATIC_ROOT: {settings.STATIC_ROOT}")
        self.stdout.write(f"  SERVE_MEDIA: {getattr(settings, 'SERVE_MEDIA', False)}")
        self.stdout.write(f"  Expected Coolify volume destination: /app/media")
        self.stdout.write(f"  MEDIA_ROOT resolves to /app/media: {'yes' if str(media_root) == '/app/media' else 'no'}")
        self.stdout.write("")

    def _media_records(self):
        from articles.models import Article
        from ask_doctor.models import DoctorMessage
        from clinic_settings.models import ClinicSetting
        from patients.models import PatientProfile
        from services.models import DentalService, ServiceImage

        records = []

        for service in DentalService.objects.exclude(image="").exclude(image__isnull=True).order_by("pk"):
            records.append(self._record("services", f"DentalService #{service.pk} legacy image", service.image))

        for image in ServiceImage.objects.select_related("service").order_by("pk"):
            records.append(self._record("services", f"ServiceImage #{image.pk} ({image.service.name})", image.image))

        for article in Article.objects.exclude(featured_image="").exclude(featured_image__isnull=True).order_by("pk"):
            records.append(self._record("articles", f"Article #{article.pk} featured image", article.featured_image))

        for article in Article.objects.exclude(content="").order_by("pk"):
            for index, name in enumerate(self._article_media_paths(article.content), start=1):
                records.append(self._path_record("articles", f"Article #{article.pk} editor image {index}", name))

        for profile in PatientProfile.objects.exclude(profile_image="").exclude(profile_image__isnull=True).order_by("pk"):
            records.append(self._record("profiles", f"PatientProfile #{profile.pk} profile image", profile.profile_image))

        for setting in ClinicSetting.objects.exclude(logo="").exclude(logo__isnull=True).order_by("pk"):
            records.append(self._record("clinic", f"ClinicSetting #{setting.pk} logo", setting.logo))

        for message in DoctorMessage.objects.exclude(attachment="").exclude(attachment__isnull=True).order_by("pk"):
            records.append(self._record("ask_doctor", f"DoctorMessage #{message.pk} attachment", message.attachment))

        return records

    def _article_media_paths(self, content):
        escaped_media_url = re.escape(settings.MEDIA_URL)
        paths = set()
        for match in re.finditer(rf"""["']([^"']*{escaped_media_url}[^"']+)["']""", content or ""):
            parsed = urlparse(match.group(1))
            path = parsed.path if parsed.path else match.group(1)
            if path.startswith(settings.MEDIA_URL):
                paths.add(unquote(path.removeprefix(settings.MEDIA_URL).lstrip("/")))
        return sorted(paths)

    def _record(self, group, label, field_file):
        return {
            "group": group,
            "label": label,
            "name": field_file.name,
            "url": field_file.url,
        }

    def _path_record(self, group, label, name):
        return {
            "group": group,
            "label": label,
            "name": name,
            "url": f"{settings.MEDIA_URL}{name}",
        }

    def _print_record(self, record, media_root):
        file_path = media_root / record["name"]

        exists = file_path.exists()
        self.stdout.write(f"  {record['label']}")
        self.stdout.write(f"    DB path: {record['name']}")
        self.stdout.write(f"    full filesystem path: {file_path}")
        self.stdout.write(f"    exists: {'yes' if exists else 'no'}")
        self.stdout.write(f"    URL: {record['url']}")
        return exists
