from io import BytesIO

from django.contrib import messages
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table

from accounts.models import User
from accounts.permissions import role_required
from .forms import InvoiceForm
from .models import Invoice


def filtered_invoices(request):
    qs = Invoice.objects.select_related("patient__user", "appointment")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(patient__user__first_name__icontains=q) | Q(patient__user__last_name__icontains=q) | Q(pk__icontains=q))
    if request.GET.get("status"):
        qs = qs.filter(status=request.GET["status"])
    if request.GET.get("date"):
        qs = qs.filter(created_at__date=request.GET["date"])
    if request.GET.get("min_amount"):
        qs = qs.filter(amount__gte=request.GET["min_amount"])
    if request.GET.get("max_amount"):
        qs = qs.filter(amount__lte=request.GET["max_amount"])
    return qs


@role_required(User.Role.ADMIN, User.Role.RECEPTIONIST)
def invoice_list(request):
    form = InvoiceForm()
    modal_open = False
    if request.method == "POST":
        form = InvoiceForm(request.POST)
        modal_open = True
        if form.is_valid():
            form.save()
            messages.success(request, "Invoice saved successfully.")
            return redirect("billing:list")
    invoices = filtered_invoices(request)
    kpis = [
        {"label": "Total Revenue", "value": invoices.filter(status=Invoice.Status.PAID).aggregate(total=Sum("amount"))["total"] or 0, "icon": "paid"},
        {"label": "Paid Invoices", "value": invoices.filter(status=Invoice.Status.PAID).count(), "icon": "task_alt"},
        {"label": "Unpaid Invoices", "value": invoices.filter(status=Invoice.Status.UNPAID).count(), "icon": "pending_actions"},
        {"label": "Cancelled Invoices", "value": invoices.filter(status=Invoice.Status.CANCELLED).count(), "icon": "cancel"},
    ]
    return render(request, "billing/invoice_list.html", {"invoices": invoices, "form": form, "modal_open": modal_open, "kpis": kpis, "status_choices": Invoice.Status.choices})


@require_POST
@role_required(User.Role.ADMIN, User.Role.RECEPTIONIST)
def invoice_status(request, pk, status):
    invoice = get_object_or_404(Invoice, pk=pk)
    if status in Invoice.Status.values:
        invoice.status = status
        invoice.save(update_fields=["status"])
    return redirect("billing:list")


@require_POST
@role_required(User.Role.ADMIN, User.Role.RECEPTIONIST)
def invoice_delete(request, pk):
    get_object_or_404(Invoice, pk=pk).delete()
    return redirect("billing:list")


def export_rows(qs):
    return [["Invoice No", "Patient", "Appointment", "Amount", "Status", "Created"]] + [[f"INV-{i.pk:05d}", str(i.patient), str(i.appointment or "-"), i.amount, i.get_status_display(), i.created_at.date()] for i in qs]


@role_required(User.Role.ADMIN, User.Role.RECEPTIONIST)
def export_pdf(request):
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="invoices.pdf"'
    buffer = BytesIO()
    SimpleDocTemplate(buffer, pagesize=A4).build([Table(export_rows(filtered_invoices(request)))])
    response.write(buffer.getvalue())
    return response


@role_required(User.Role.ADMIN, User.Role.RECEPTIONIST)
def export_excel(request):
    wb = Workbook()
    ws = wb.active
    for row in export_rows(filtered_invoices(request)):
        ws.append(row)
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="invoices.xlsx"'
    wb.save(response)
    return response
