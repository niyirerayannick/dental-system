import os

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
IMAGE_FORMATS = {"JPEG", "PNG", "GIF", "WEBP"}

ATTACHMENT_EXTENSIONS = IMAGE_EXTENSIONS | {".pdf", ".doc", ".docx"}
ATTACHMENT_CONTENT_TYPES = IMAGE_CONTENT_TYPES | {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

DEFAULT_MAX_IMAGE_SIZE = 5 * 1024 * 1024
DEFAULT_MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024


def _extension(upload):
    return os.path.splitext(upload.name or "")[1].lower()


def _content_type(upload):
    return (getattr(upload, "content_type", "") or "").lower()


def _ensure_rewound(upload):
    if hasattr(upload, "seek"):
        upload.seek(0)


def validate_uploaded_image(upload, *, max_size=DEFAULT_MAX_IMAGE_SIZE):
    if not upload:
        return
    if getattr(upload, "size", 0) > max_size:
        raise ValidationError(f"Image must be {max_size // (1024 * 1024)} MB or less.")
    if _extension(upload) not in IMAGE_EXTENSIONS:
        raise ValidationError("Upload a JPG, PNG, GIF, or WebP image.")
    if _content_type(upload) not in IMAGE_CONTENT_TYPES:
        raise ValidationError("Upload a JPG, PNG, GIF, or WebP image.")

    try:
        _ensure_rewound(upload)
        with Image.open(upload) as image:
            image.verify()
            if image.format not in IMAGE_FORMATS:
                raise ValidationError("Upload a JPG, PNG, GIF, or WebP image.")
    except (UnidentifiedImageError, OSError):
        raise ValidationError("Upload a valid image file.")
    finally:
        _ensure_rewound(upload)


def validate_uploaded_attachment(upload, *, max_size=DEFAULT_MAX_ATTACHMENT_SIZE):
    if not upload:
        return
    if getattr(upload, "size", 0) > max_size:
        raise ValidationError(f"Attachment must be {max_size // (1024 * 1024)} MB or less.")

    ext = _extension(upload)
    content_type = _content_type(upload)
    if ext not in ATTACHMENT_EXTENSIONS or content_type not in ATTACHMENT_CONTENT_TYPES:
        raise ValidationError("Upload an image, PDF, DOC, or DOCX file.")

    if ext in IMAGE_EXTENSIONS:
        validate_uploaded_image(upload, max_size=max_size)
        return

    _ensure_rewound(upload)
    header = upload.read(8)
    _ensure_rewound(upload)

    if ext == ".pdf" and not header.startswith(b"%PDF"):
        raise ValidationError("Upload a valid PDF file.")
    if ext == ".docx" and not header.startswith(b"PK"):
        raise ValidationError("Upload a valid DOCX file.")
    if ext == ".doc" and not header.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        raise ValidationError("Upload a valid DOC file.")
