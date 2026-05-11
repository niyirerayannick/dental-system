from django.urls import path

from .views import export_excel, export_pdf, invoice_delete, invoice_list, invoice_status

app_name = "billing"

urlpatterns = [
    path("", invoice_list, name="list"),
    path("<int:pk>/status/<str:status>/", invoice_status, name="status"),
    path("<int:pk>/delete/", invoice_delete, name="delete"),
    path("export/pdf/", export_pdf, name="export_pdf"),
    path("export/excel/", export_excel, name="export_excel"),
]
