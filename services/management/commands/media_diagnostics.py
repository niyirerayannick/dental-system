from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Print media storage diagnostics for production deployments."

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)
        base_dir = Path(settings.BASE_DIR)
        service_upload_target = media_root / "services"

        self.stdout.write(f"BASE_DIR: {base_dir}")
        self.stdout.write(f"MEDIA_URL: {settings.MEDIA_URL}")
        self.stdout.write(f"MEDIA_ROOT: {media_root}")
        self.stdout.write(f"SERVE_MEDIA: {getattr(settings, 'SERVE_MEDIA', False)}")
        self.stdout.write(f"Service upload target: {service_upload_target}")
        self.stdout.write(f"MEDIA_ROOT exists: {media_root.exists()}")
        self.stdout.write(f"MEDIA_ROOT writable: {self._is_writable(media_root)}")

        self._print_model_files()

    def _is_writable(self, path):
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".media_write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return True
        except OSError:
            return False

    def _print_model_files(self):
        from articles.models import Article
        from patients.models import PatientProfile
        from services.models import DentalService, ServiceImage

        checks = [
            ("Service featured image", DentalService.objects.exclude(image="").exclude(image__isnull=True), "image"),
            ("Service gallery image", ServiceImage.objects.exclude(image="").exclude(image__isnull=True), "image"),
            ("Article featured image", Article.objects.exclude(featured_image="").exclude(featured_image__isnull=True), "featured_image"),
            ("Patient profile image", PatientProfile.objects.exclude(profile_image="").exclude(profile_image__isnull=True), "profile_image"),
        ]

        for label, queryset, field_name in checks:
            self.stdout.write("")
            self.stdout.write(f"{label}:")
            obj = queryset.first()
            if not obj:
                self.stdout.write("  No uploaded file found.")
                continue

            field_file = getattr(obj, field_name)
            try:
                file_path = Path(field_file.path)
            except NotImplementedError:
                file_path = None

            self.stdout.write(f"  URL: {field_file.url}")
            self.stdout.write(f"  Relative name: {field_file.name}")
            self.stdout.write(f"  Filesystem path: {file_path or 'not available for this storage backend'}")
            if file_path:
                self.stdout.write(f"  Exists on disk: {file_path.exists()}")
                self.stdout.write(f"  Under MEDIA_ROOT: {self._is_relative_to(file_path, Path(settings.MEDIA_ROOT))}")

        self.stdout.write("")
        self.stdout.write("Dentist photos:")
        self.stdout.write("  No dentist photo ImageField exists on DentistProfile in this codebase.")

    def _is_relative_to(self, child, parent):
        try:
            child.resolve().relative_to(parent.resolve())
            return True
        except ValueError:
            return False
