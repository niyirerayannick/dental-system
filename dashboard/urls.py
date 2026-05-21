from django.urls import path

from .views import (
    admin_dashboard,
    dentist_dashboard,
    patient_appointments_page,
    patient_book_page,
    patient_cancel_appointment,
    patient_dashboard,
    patient_invoices_page,
    patient_notifications_page,
    patient_profile_page,
    patient_treatments_page,
    receptionist_appointments_page,
    receptionist_dashboard,
    receptionist_notifications_page,
    receptionist_profile_page,
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
    path("receptionist/appointments/", receptionist_appointments_page, name="receptionist_appointments"),
    path("receptionist/notifications/", receptionist_notifications_page, name="receptionist_notifications"),
    path("receptionist/profile/", receptionist_profile_page, name="receptionist_profile"),
    path("patient/", patient_dashboard, name="patient"),
    path("patient/appointments/<int:pk>/cancel/", patient_cancel_appointment, name="patient_cancel_appointment"),
    path("patient/appointments/", patient_appointments_page, name="patient_appointments"),
    path("patient/book/", patient_book_page, name="patient_book"),
    path("patient/notifications/", patient_notifications_page, name="patient_notifications"),
    path("patient/treatments/", patient_treatments_page, name="patient_treatments"),
    path("patient/invoices/", patient_invoices_page, name="patient_invoices"),
    path("patient/profile/", patient_profile_page, name="patient_profile"),
]
