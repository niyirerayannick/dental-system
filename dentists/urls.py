from django.urls import path

from .views import dentist_delete, dentist_list, export_excel, export_pdf

app_name = "dentists"

urlpatterns = [
    path("", dentist_list, name="list"),
    path("<int:pk>/delete/", dentist_delete, name="delete"),
    path("export/pdf/", export_pdf, name="export_pdf"),
    path("export/excel/", export_excel, name="export_excel"),
]
