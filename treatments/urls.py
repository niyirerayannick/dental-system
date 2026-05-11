from django.urls import path

from .views import export_excel, export_pdf, treatment_delete, treatment_list

app_name = "treatments"

urlpatterns = [
    path("", treatment_list, name="list"),
    path("<int:pk>/delete/", treatment_delete, name="delete"),
    path("export/pdf/", export_pdf, name="export_pdf"),
    path("export/excel/", export_excel, name="export_excel"),
]
