from django.urls import path

from .views import export_excel, export_pdf, invoice_delete, invoice_json, invoice_list, invoice_status, invoice_update

app_name = "billing"

urlpatterns = [
    path("", invoice_list, name="list"),
    path("<int:pk>/json/", invoice_json, name="json"),
    path("<int:pk>/update/", invoice_update, name="update"),
    path("<int:pk>/mark-paid/", invoice_status, {"status": "paid"}, name="mark_paid"),
    path("<int:pk>/cancel/", invoice_status, {"status": "cancelled"}, name="cancel"),
    path("<int:pk>/status/<str:status>/", invoice_status, name="status"),
    path("<int:pk>/delete/", invoice_delete, name="delete"),
    path("export/pdf/", export_pdf, name="export_pdf"),
    path("export/excel/", export_excel, name="export_excel"),
]
