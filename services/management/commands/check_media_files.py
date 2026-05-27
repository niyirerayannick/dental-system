from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import OperationalError


class Command(BaseCommand):
    help = "Check uploaded service media configuration and file availability."

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)
        self.stdout.write(f"MEDIA_ROOT path: {media_root}")
        self.stdout.write(f"MEDIA_URL: {settings.MEDIA_URL}")
        self.stdout.write(f"Media folder exists: {media_root.exists()}")
        self.stdout.write(f"Services media folder exists: {(media_root / 'services').exists()}")
        self.stdout.write(f"SERVE_MEDIA: {getattr(settings, 'SERVE_MEDIA', False)}")
        self.stdout.write("")

        try:
            self._print_services(media_root)
        except OperationalError as exc:
            self.stdout.write(self.style.ERROR("Could not query services."))
            self.stdout.write(str(exc))

    def _print_services(self, media_root):
        from services.models import DentalService

        services = (
            DentalService.objects.select_related("category")
            .prefetch_related("gallery_images")
            .order_by("pk")[:5]
        )

        if not services:
            self.stdout.write("No services found.")
            return

        for service in services:
            self.stdout.write(f"Service #{service.pk}: {service.name}")
            self._print_field_file("  legacy image", service.image, media_root)

            gallery_images = list(service.gallery_images.all())
            if gallery_images:
                for index, gallery_image in enumerate(gallery_images, start=1):
                    self._print_field_file(f"  gallery image {index}", gallery_image.image, media_root)
            else:
                self.stdout.write("  gallery images: none")
            self.stdout.write("")

    def _print_field_file(self, label, field_file, media_root):
        value = field_file.name if field_file else ""
        self.stdout.write(f"{label} field value: {value or '(empty)'}")

        if not field_file:
            return

        try:
            file_path = Path(field_file.path)
        except NotImplementedError:
            file_path = media_root / field_file.name

        self.stdout.write(f"{label} full file path: {file_path}")
        self.stdout.write(f"{label} exists on disk: {file_path.exists()}")
        self.stdout.write(f"{label} image URL: {field_file.url}")
