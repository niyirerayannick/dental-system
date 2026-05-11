from django.urls import path

from .views import (
    appointment_delete,
    appointment_list,
    appointment_status,
    appointment_json,
    appointment_update,
    available_slots_api,
    dentist_availability_api,
    export_excel,
    export_pdf,
)

app_name = "appointments"

urlpatterns = [
    path("", appointment_list, name="list"),
    path("api/dentist-availability/<int:dentist_id>/", dentist_availability_api, name="dentist_availability_api"),
    path("api/available-slots/", available_slots_api, name="available_slots_api"),
    path("<int:pk>/json/", appointment_json, name="json"),
    path("<int:pk>/update/", appointment_update, name="update"),
    path("<int:pk>/approve/", appointment_status, {"status": "approved"}, name="approve"),
    path("<int:pk>/complete/", appointment_status, {"status": "completed"}, name="complete"),
    path("<int:pk>/cancel/", appointment_status, {"status": "cancelled"}, name="cancel"),
    path("<int:pk>/status/<str:status>/", appointment_status, name="status"),
    path("<int:pk>/delete/", appointment_delete, name="delete"),
    path("export/pdf/", export_pdf, name="export_pdf"),
    path("export/excel/", export_excel, name="export_excel"),
]
