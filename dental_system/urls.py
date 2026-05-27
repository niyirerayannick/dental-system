from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from .views import health, home, public_book, public_contact, public_service_detail, public_services
from notifications.views import twilio_status_callback

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("api/twilio/status-callback/", twilio_status_callback, name="twilio_status_callback"),
    path("", home, name="home"),
    # Public pages
    path("services/", public_services, name="pub_services"),
    path("services/<slug:slug>/", public_service_detail, name="pub_service_detail"),
    path("book/", public_book, name="pub_book"),
    path("ask-doctor/", include("ask_doctor.urls", namespace="ask_doctor")),
    path("education/", include("articles.urls", namespace="articles")),
    path("contact/", public_contact, name="pub_contact"),
    # Dashboard apps
    path("accounts/", include("accounts.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("patients/", include("patients.urls")),
    path("dentists/", include("dentists.urls")),
    path("appointments/", include("appointments.urls")),
    path("treatments/", include("treatments.urls")),
    path("billing/", include("billing.urls")),
    path("reports/", include("reports.urls")),
    path("settings/", include("clinic_settings.urls")),
    path("notifications/", include("notifications.urls")),
    path("manage/services/", include("services.urls")),
    path("followups/", include("followups.urls", namespace="followups")),
    path("tinymce/", include("tinymce.urls")),
]

if settings.DEBUG or getattr(settings, "SERVE_MEDIA", False):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
