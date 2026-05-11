from django.urls import path

from .views import export_excel, export_pdf, report_list

app_name = "reports"

urlpatterns = [
    path("", report_list, name="list"),
    path("export/pdf/", export_pdf, name="export_pdf"),
    path("export/excel/", export_excel, name="export_excel"),
]
