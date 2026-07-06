from pathlib import Path

import dj_database_url
from decouple import AutoConfig, Csv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
config = AutoConfig(search_path=BASE_DIR)


def cast_debug(value):
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on", "dev", "development"}:
        return True
    if normalized in {"0", "false", "no", "off", "prod", "production", "release"}:
        return False
    raise ValueError(f"Invalid DEBUG value: {value}")


SECRET_KEY = config("SECRET_KEY", default="django-insecure-change-me")
DEBUG = config("DEBUG", default=True, cast=cast_debug)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())

if not DEBUG and SECRET_KEY.startswith("django-insecure"):
    raise ImproperlyConfigured("Set a secure SECRET_KEY when DEBUG=False.")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "patients",
    "dentists",
    "appointments",
    "treatments",
    "billing",
    "dashboard",
    "reports",
    "clinic_settings",
    "notifications",
    "services",
    "articles",
    "ask_doctor",
    "followups",
    "tinymce",
]

LOGIN_URL = "/accounts/login/"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

CSRF_TRUSTED_ORIGINS = [origin for origin in CSRF_TRUSTED_ORIGINS if origin]

ROOT_URLCONF = "dental_system.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "dashboard.context_processors.dashboard_navigation",
            ],
        },
    },
]

WSGI_APPLICATION = "dental_system.wsgi.application"

DATABASE_URL = config("DATABASE_URL", default="").strip()
PLACEHOLDER_DATABASE_URLS = {
    "postgres://username:password@host:5432/database_name",
    "postgresql://username:password@host:5432/database_name",
}

if DATABASE_URL in PLACEHOLDER_DATABASE_URLS:
    DATABASE_URL = ""

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=config("DATABASE_CONN_MAX_AGE", default=600, cast=int),
            conn_health_checks=True,
        )
    }
elif DEBUG:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": config("SQLITE_NAME", default=str(BASE_DIR / "db.sqlite3")),
        }
    }
else:
    raise ImproperlyConfigured(
        "DATABASE_URL is required when DEBUG=False. Use the Coolify PostgreSQL connection string."
    )

if not DEBUG and DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":
    raise ImproperlyConfigured("SQLite is not allowed in production. Set DATABASE_URL to PostgreSQL.")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = config("TIME_ZONE", default="Africa/Kigali")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
# WhiteNoise serves static files only, never uploaded media.
# In Coolify, mount host /var/www/dentalcare/media to container /app/media so uploads
# survive redeploys. Serve /media/ via the reverse proxy (see deploy/) or Django below.
# Private paths such as ask_doctor/attachments/ must route through Django when using
# direct file serving at the proxy.
SERVE_MEDIA = config("SERVE_MEDIA", default=True, cast=bool)

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:redirect"
LOGOUT_REDIRECT_URL = "home"
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "accounts.backends.EmailOrPhoneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

TWILIO_ACCOUNT_SID = config("TWILIO_ACCOUNT_SID", default="")
TWILIO_AUTH_TOKEN = config("TWILIO_AUTH_TOKEN", default="")
TWILIO_SMS_FROM = config("TWILIO_SMS_FROM", default="")
TWILIO_WHATSAPP_FROM = config("TWILIO_WHATSAPP_FROM", default="whatsapp:+14155238886")
TWILIO_STATUS_CALLBACK_URL = config("TWILIO_STATUS_CALLBACK_URL", default="")
TWILIO_VALIDATE_SIGNATURE = config("TWILIO_VALIDATE_SIGNATURE", default=not DEBUG, cast=bool)
NOTIFICATION_PREFERRED_CHANNEL = config("NOTIFICATION_PREFERRED_CHANNEL", default="sms").strip().lower()
CLINIC_NAME = config("CLINIC_NAME", default="Plan Healthcare Clinic")
CLINIC_PHONE = config("CLINIC_PHONE", default="0780474044")

TINYMCE_DEFAULT_CONFIG = {
    "height": 500,
    "plugins": "advlist autolink lists link image charmap preview anchor searchreplace visualblocks code fullscreen insertdatetime media table help wordcount",
    "toolbar": "undo redo | blocks | bold italic underline | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | link image media | blockquote code | table | removeformat | help",
    "menubar": "file edit view insert format tools table help",
    "images_upload_url": "/dashboard/articles/image-upload/",
    "images_upload_credentials": True,
    "automatic_uploads": True,
    "file_picker_types": "image",
    "media_live_embeds": True,
    "extended_valid_elements": "iframe[src|frameborder|class|width|height|allow|allowfullscreen]",
    "valid_elements": "p,br,strong/b,em/i,u,ul,ol,li,blockquote,code,pre,h2,h3,h4,a[href|target|rel],img[src|alt|width|height],table,thead,tbody,tr,th,td",
}

SESSION_COOKIE_AGE = 60 * 60 * 24 * 365  # 1 year — session never times out; only logout clears it
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = config("CSRF_COOKIE_HTTPONLY", default=False, cast=bool)
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=not DEBUG, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=not DEBUG, cast=bool)
SESSION_COOKIE_SAMESITE = config("SESSION_COOKIE_SAMESITE", default="Lax")
CSRF_COOKIE_SAMESITE = config("CSRF_COOKIE_SAMESITE", default="Lax")
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=not DEBUG, cast=bool)
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=0, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False, cast=bool)
SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=False, cast=bool)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

if config("USE_X_FORWARDED_HOST", default=not DEBUG, cast=bool):
    USE_X_FORWARDED_HOST = True

if config("SECURE_PROXY_SSL_HEADER", default=not DEBUG, cast=bool):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
