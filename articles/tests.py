from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from accounts.models import User


def make_image_upload(name="photo.png", content_type="image/png"):
    buffer = BytesIO()
    Image.new("RGB", (10, 10), color="white").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)


class ArticleImageUploadTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            phone="+250780000001",
            password="pass12345",
            first_name="Admin",
            last_name="User",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.client.force_login(self.admin)

    def test_rejects_svg_upload(self):
        upload = SimpleUploadedFile(
            "bad.svg",
            b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>",
            content_type="image/svg+xml",
        )

        response = self.client.post("/education/dashboard/image-upload/", {"file": upload})

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_accepts_valid_raster_image(self):
        response = self.client.post("/education/dashboard/image-upload/", {"file": make_image_upload()})

        self.assertEqual(response.status_code, 200)
        self.assertIn("/media/articles/uploads/", response.json()["location"])


class PublicMediaServingTests(TestCase):
    def test_public_media_file_opens_from_media_url(self):
        with TemporaryDirectory() as temp_dir, self.settings(MEDIA_ROOT=Path(temp_dir), SERVE_MEDIA=True):
            from django.conf import settings

            media_root = settings.MEDIA_ROOT
            file_path = media_root / "services" / "example.jpg"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(b"example")

            response = self.client.get("/media/services/example.jpg")

            self.assertEqual(response.status_code, 200)
            response.close()
