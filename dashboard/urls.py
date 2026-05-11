from django.urls import path

from .views import (
    admin_dashboard,
    dentist_dashboard,
    patient_cancel_appointment,
    patient_dashboard,
    receptionist_dashboard,
    role_dashboard_redirect,
    update_appointment_status,
)

app_name = "dashboard"

urlpatterns = [
    path("", role_dashboard_redirect, name="redirect"),
    path("admin/", admin_dashboard, name="admin"),
    path("dentist/", dentist_dashboard, name="dentist"),
    path("dentist/appointments/<int:pk>/<str:status>/", update_appointment_status, name="dentist_appointment_status"),
    path("receptionist/", receptionist_dashboard, name="receptionist"),
    path("patient/", patient_dashboard, name="patient"),
    path("patient/appointments/<int:pk>/cancel/", patient_cancel_appointment, name="patient_cancel_appointment"),
]
