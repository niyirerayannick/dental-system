import re
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import OperationalError

from dental_system.media_storage import (
    COOLIFY_MEDIA_CONTAINER_PATH,
    COOLIFY_MEDIA_HOST_PATH,
    is_media_mount_persistent,
)


class Command(BaseCommand):
    help = "Diagnose database, media storage, permissions, and uploaded file health."

    def add_arguments(self, parser):
        parser.add_argument(
            "--deploy-check",
            action="store_true",
            help="Exit with an error when production media storage is not persistent or files are missing.",
        )

    def handle(self, *args, **options):
        deploy_check = options["deploy_check"]
        media_root = Path(settings.MEDIA_ROOT)
        mount_persistent = is_media_mount_persistent(media_root)

        self._print_database()
        self._print_storage(media_root, mount_persistent)
        self._print_permissions(media_root)
        self._print_sample_files(media_root)

        broken = []
        records = []

        try:
            records = self._media_records()
        except OperationalError as exc:
            self.stdout.write(self.style.ERROR("Could not query media records."))
            self.stdout.write(str(exc))
            if deploy_check:
                raise CommandError("Database media query failed.") from exc
            return

        service_images = [record for record in records if record["group"] == "services"]

        self.stdout.write("Database media references:")
        self.stdout.write(f"  Service image references: {len(service_images)}")
        self.stdout.write(f"  All uploaded media references: {len(records)}")
        self.stdout.write("")

        self.stdout.write("Sample DB records:")
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

        if deploy_check:
            self._run_deploy_check(
                media_root=media_root,
                mount_persistent=mount_persistent,
                broken_count=len(broken),
                record_count=len(records),
            )

    def _run_deploy_check(self, media_root, mount_persistent, broken_count, record_count):
        problems = []

        if not settings.DEBUG and str(media_root) != COOLIFY_MEDIA_CONTAINER_PATH:
            problems.append(f"MEDIA_ROOT should be {COOLIFY_MEDIA_CONTAINER_PATH} in production.")

        if mount_persistent is False:
            problems.append(
                "Persistent volume is NOT mounted at /app/media. "
                f"Add Coolify storage: {COOLIFY_MEDIA_HOST_PATH} -> {COOLIFY_MEDIA_CONTAINER_PATH}"
            )

        if not media_root.exists() or not self._is_writable(media_root):
            problems.append("Media folder is missing or not writable.")

        if broken_count:
            problems.append(
                f"{broken_count} database file reference(s) point to missing files on disk. "
                "Re-upload images or restore /var/www/dentalcare/media from backup."
            )

        if problems:
            self.stdout.write("")
            self.stdout.write(self.style.ERROR("Deploy check failed:"))
            for problem in problems:
                self.stdout.write(self.style.ERROR(f"  - {problem}"))
            raise CommandError("Media storage is not safe for production redeploys.")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Deploy check passed: media storage looks persistent."))
        if record_count == 0:
            self.stdout.write("  No uploads in database yet. Upload a test image after deploy.")

    def _print_database(self):
        database = settings.DATABASES["default"]
        engine = database.get("ENGINE", "")
        name = database.get("NAME", "")
        host = database.get("HOST", "") or "(local file)" if "sqlite" in engine else "(default)"

        self.stdout.write("Database:")
        self.stdout.write(f"  ENGINE: {engine}")
        self.stdout.write(f"  NAME: {self._masked(name)}")
        if "postgresql" in engine:
            self.stdout.write(f"  HOST: {host}")
            self.stdout.write(f"  PORT: {database.get('PORT', '') or '(default)'}")
            self.stdout.write(f"  USER: {database.get('USER', '') or '(default)'}")
        self.stdout.write(f"  PostgreSQL in production: {'yes' if 'postgresql' in engine else 'no'}")
        self.stdout.write(f"  SQLite fallback active: {'yes' if 'sqlite' in engine else 'no'}")
        self.stdout.write("")

    def _print_storage(self, media_root, mount_persistent):
        self.stdout.write("Media storage:")
        self.stdout.write(f"  BASE_DIR: {settings.BASE_DIR}")
        self.stdout.write(f"  MEDIA_ROOT: {media_root}")
        self.stdout.write(f"  MEDIA_URL: {settings.MEDIA_URL}")
        self.stdout.write(f"  STATIC_URL: {settings.STATIC_URL}")
        self.stdout.write(f"  STATIC_ROOT: {settings.STATIC_ROOT}")
        self.stdout.write(f"  SERVE_MEDIA: {getattr(settings, 'SERVE_MEDIA', False)}")
        self.stdout.write(f"  Coolify host source path: {COOLIFY_MEDIA_HOST_PATH}")
        self.stdout.write(f"  Coolify container destination: {COOLIFY_MEDIA_CONTAINER_PATH}")
        self.stdout.write(
            f"  MEDIA_ROOT matches container mount: {'yes' if str(media_root) == COOLIFY_MEDIA_CONTAINER_PATH else 'no'}"
        )
        if mount_persistent is None:
            self.stdout.write("  persistent volume mounted: unknown (not running in Linux container)")
        else:
            self.stdout.write(f"  persistent volume mounted: {'yes' if mount_persistent else 'no'}")
        self.stdout.write("")

    def _print_permissions(self, media_root):
        exists = media_root.exists()
        writable = self._is_writable(media_root) if exists or self._ensure_dir(media_root) else False

        self.stdout.write("Media folder:")
        self.stdout.write(f"  exists: {'yes' if exists or media_root.exists() else 'no'}")
        self.stdout.write(f"  writable: {'yes' if writable else 'no'}")
        self.stdout.write("")

    def _print_sample_files(self, media_root):
        services_dir = media_root / "services"
        sample_files = []

        if services_dir.is_dir():
            sample_files.extend(sorted(services_dir.iterdir())[:5])

        if not sample_files and media_root.exists():
            for path in sorted(media_root.rglob("*")):
                if path.is_file():
                    sample_files.append(path)
                if len(sample_files) >= 5:
                    break

        self.stdout.write("Sample files on disk:")
        self.stdout.write(f"  services/ folder exists: {'yes' if services_dir.is_dir() else 'no'}")
        self.stdout.write(f"  sample files exist: {'yes' if sample_files else 'no'}")
        if sample_files:
            for path in sample_files:
                relative = path.relative_to(media_root)
                self.stdout.write(f"    - {relative}")
        self.stdout.write("")

    def _ensure_dir(self, media_root):
        try:
            media_root.mkdir(parents=True, exist_ok=True)
            return True
        except OSError:
            return False

    def _is_writable(self, media_root):
        probe = media_root / ".media_write_test"
        try:
            media_root.mkdir(parents=True, exist_ok=True)
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return True
        except OSError:
            probe.unlink(missing_ok=True)
            return False

    def _masked(self, value):
        value = str(value or "")
        if not value:
            return "(empty)"
        if len(value) <= 8:
            return value
        return f"{value[:4]}...{value[-4:]}"

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
