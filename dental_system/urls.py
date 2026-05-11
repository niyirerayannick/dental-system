from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from .views import home

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("accounts/", include("accounts.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("patients/", include("patients.urls")),
    path("dentists/", include("dentists.urls")),
    path("appointments/", include("appointments.urls")),
    path("treatments/", include("treatments.urls")),
    path("billing/", include("billing.urls")),
    path("reports/", include("reports.urls")),
    path("settings/", include("clinic_settings.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
