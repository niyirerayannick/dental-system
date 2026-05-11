from django.urls import path

from .views import appointment_delete, appointment_list, appointment_status, export_excel, export_pdf

app_name = "appointments"

urlpatterns = [
    path("", appointment_list, name="list"),
    path("<int:pk>/status/<str:status>/", appointment_status, name="status"),
    path("<int:pk>/delete/", appointment_delete, name="delete"),
    path("export/pdf/", export_pdf, name="export_pdf"),
    path("export/excel/", export_excel, name="export_excel"),
]
