from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from accounts.models import User
from ask_doctor.forms import SendMessageForm
from ask_doctor.models import DoctorConversation, DoctorMessage


def make_image_upload(name="photo.png", content_type="image/png"):
    buffer = BytesIO()
    Image.new("RGB", (10, 10), color="white").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)


class AskDoctorAttachmentValidationTests(TestCase):
    def test_rejects_html_attachment_even_if_uploaded(self):
        form = SendMessageForm(
            data={"message": "Please review this."},
            files={
                "attachment": SimpleUploadedFile(
                    "payload.html",
                    b"<script>alert(1)</script>",
                    content_type="text/html",
                )
            },
        )

        self.assertFalse(form.is_valid())
        self.assertIn("attachment", form.errors)

    def test_accepts_valid_image_attachment(self):
        form = SendMessageForm(
            data={"message": "Please review this."},
            files={"attachment": make_image_upload()},
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_patient_view_rejects_invalid_attachment(self):
        patient = User.objects.create_user(
            phone="+250780000002",
            password="pass12345",
            first_name="Patient",
            last_name="User",
            role=User.Role.PATIENT,
        )
        self.client.force_login(patient)
        upload = SimpleUploadedFile("payload.html", b"<h1>bad</h1>", content_type="text/html")

        response = self.client.post(
            "/ask-doctor/form/",
            {"subject": "Question", "message": "Please review this.", "attachment": upload},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upload an image, PDF, DOC, or DOCX file.")


class AskDoctorPrivateMediaTests(TestCase):
    def test_ask_doctor_attachment_requires_conversation_access(self):
        with TemporaryDirectory() as temp_dir, self.settings(MEDIA_ROOT=Path(temp_dir), SERVE_MEDIA=True):
            from django.conf import settings

            patient = User.objects.create_user(
                phone="+250780000003",
                password="pass12345",
                first_name="Patient",
                last_name="Owner",
                role=User.Role.PATIENT,
            )
            other = User.objects.create_user(
                phone="+250780000004",
                password="pass12345",
                first_name="Other",
                last_name="Patient",
                role=User.Role.PATIENT,
            )
            conversation = DoctorConversation.objects.create(patient=patient)
            file_path = settings.MEDIA_ROOT / "ask_doctor" / "attachments" / "note.pdf"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(b"%PDF test")
            DoctorMessage.objects.create(
                conversation=conversation,
                sender=patient,
                message="Please review",
                attachment="ask_doctor/attachments/note.pdf",
            )

            self.client.force_login(other)
            denied = self.client.get("/media/ask_doctor/attachments/note.pdf")
            self.assertEqual(denied.status_code, 403)

            self.client.force_login(patient)
            allowed = self.client.get("/media/ask_doctor/attachments/note.pdf")
            self.assertEqual(allowed.status_code, 200)
            allowed.close()
