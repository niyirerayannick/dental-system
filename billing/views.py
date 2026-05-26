from io import BytesIO

from django.contrib import messages
from django.db.models import Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table

from accounts.models import User
from accounts.permissions import role_required
from .forms import InvoiceForm
from .models import Invoice


def _dashboard_base_ctx(user):
    from notifications.models import Notification
    if user.role == User.Role.RECEPTIONIST:
        return {
            "base_template": "dashboard/receptionist_base.html",
            "unread_count": Notification.objects.filter(user=user, is_read=False).count(),
        }
    return {"base_template": "dashboard/base.html"}


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


@role_required(User.Role.ADMIN)
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
    ctx = _dashboard_base_ctx(request.user)
    ctx.update({"invoices": invoices, "form": form, "modal_open": modal_open, "kpis": kpis, "status_choices": Invoice.Status.choices})
    return render(request, "billing/invoice_list.html", ctx)


@require_POST
@role_required(User.Role.ADMIN)
def invoice_status(request, pk, status):
    invoice = get_object_or_404(Invoice, pk=pk)
    if status in Invoice.Status.values:
        invoice.status = status
        invoice.save(update_fields=["status"])
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "message": "Invoice status updated.", "record": invoice_payload(invoice)})
    return redirect("billing:list")


@require_POST
@role_required(User.Role.ADMIN)
def invoice_delete(request, pk):
    get_object_or_404(Invoice, pk=pk).delete()
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "message": "Invoice deleted."})
    return redirect("billing:list")


def invoice_payload(invoice):
    return {
        "id": invoice.pk,
        "patient": invoice.patient_id,
        "appointment": invoice.appointment_id or "",
        "amount": str(invoice.amount),
        "status": invoice.status,
        "display": {
            "number": f"INV-{invoice.pk:05d}",
            "patient": str(invoice.patient),
            "appointment": str(invoice.appointment or "-"),
            "amount": str(invoice.amount),
            "status": invoice.get_status_display(),
        },
    }


@role_required(User.Role.ADMIN)
def invoice_json(request, pk):
    invoice = get_object_or_404(Invoice.objects.select_related("patient__user", "appointment"), pk=pk)
    return JsonResponse({"ok": True, "record": invoice_payload(invoice)})


@require_POST
@role_required(User.Role.ADMIN)
def invoice_update(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    form = InvoiceForm(request.POST, instance=invoice)
    if form.is_valid():
        invoice = form.save()
        return JsonResponse({"ok": True, "message": "Invoice updated successfully.", "record": invoice_payload(invoice)})
    return JsonResponse({"ok": False, "message": "Please correct the invoice form errors.", "errors": form.errors}, status=400)


def export_rows(qs):
    return [["Invoice No", "Patient", "Appointment", "Amount", "Status", "Created"]] + [[f"INV-{i.pk:05d}", str(i.patient), str(i.appointment or "-"), i.amount, i.get_status_display(), i.created_at.date()] for i in qs]


@role_required(User.Role.ADMIN)
def export_pdf(request):
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="invoices.pdf"'
    buffer = BytesIO()
    SimpleDocTemplate(buffer, pagesize=A4).build([Table(export_rows(filtered_invoices(request)))])
    response.write(buffer.getvalue())
    return response


@role_required(User.Role.ADMIN)
def export_excel(request):
    wb = Workbook()
    ws = wb.active
    for row in export_rows(filtered_invoices(request)):
        ws.append(row)
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="invoices.xlsx"'
    wb.save(response)
    return response
