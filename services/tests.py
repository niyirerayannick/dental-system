from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from services.views import _validate_service_images


def make_image_upload(name="photo.png", content_type="image/png"):
    buffer = BytesIO()
    Image.new("RGB", (10, 10), color="white").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)


class ServiceImageValidationTests(TestCase):
    def test_rejects_non_image_gallery_upload(self):
        upload = SimpleUploadedFile("not-image.txt", b"plain text", content_type="text/plain")

        with self.assertRaises(ValidationError):
            _validate_service_images([upload])

    def test_accepts_valid_gallery_image(self):
        _validate_service_images([make_image_upload()])
