from django.urls import path

from .views import (
    export_patients_excel,
    export_patients_pdf,
    patient_create,
    patient_delete,
    patient_detail,
    patient_edit,
    patient_json,
    patient_list,
    patient_update,
)

app_name = "patients"

urlpatterns = [
    path("", patient_list, name="list"),
    path("add/", patient_create, name="add"),
    path("<int:pk>/json/", patient_json, name="json"),
    path("<int:pk>/update/", patient_update, name="update"),
    path("<int:pk>/", patient_detail, name="detail"),
    path("<int:pk>/edit/", patient_edit, name="edit"),
    path("<int:pk>/delete/", patient_delete, name="delete"),
    path("export/pdf/", export_patients_pdf, name="export_pdf"),
    path("export/excel/", export_patients_excel, name="export_excel"),
]
