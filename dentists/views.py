from io import BytesIO

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table

from accounts.models import User
from accounts.permissions import role_required
from appointments.models import Appointment
from .forms import DentistForm
from .models import DentistProfile


def filtered_dentists(request):
    qs = DentistProfile.objects.select_related("user")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q) | Q(user__email__icontains=q) | Q(user__phone__icontains=q) | Q(license_number__icontains=q))
    if request.GET.get("specialization"):
        qs = qs.filter(specialization__icontains=request.GET["specialization"])
    if request.GET.get("availability"):
        qs = qs.filter(available_days__icontains=request.GET["availability"])
    return qs


@role_required(User.Role.ADMIN, User.Role.RECEPTIONIST)
def dentist_list(request):
    form = DentistForm()
    modal_open = False
    if request.method == "POST":
        form = DentistForm(request.POST)
        modal_open = True
        if form.is_valid():
            form.save()
            messages.success(request, "Dentist created successfully.")
            return redirect("dentists:list")
    dentists = filtered_dentists(request)
    today = timezone.localdate()
    kpis = [
        {"label": "Total Dentists", "value": dentists.count(), "icon": "dentistry"},
        {"label": "Available Dentists", "value": dentists.filter(user__is_active=True).count(), "icon": "verified_user"},
        {"label": "Specialists", "value": dentists.exclude(specialization="").count(), "icon": "medical_services"},
        {"label": "Appointments Today", "value": Appointment.objects.filter(appointment_date=today).count(), "icon": "calendar_today"},
    ]
    return render(request, "dentists/dentist_list.html", {"dentists": dentists, "form": form, "modal_open": modal_open, "kpis": kpis})


@require_POST
@role_required(User.Role.ADMIN, User.Role.RECEPTIONIST)
def dentist_delete(request, pk):
    dentist = get_object_or_404(DentistProfile.objects.select_related("user"), pk=pk)
    dentist.user.delete()
    messages.success(request, "Dentist deleted.")
    return redirect("dentists:list")


def export_rows(qs):
    return [["Dentist", "Email", "Phone", "Specialization", "License", "Available Days", "Status"]] + [[str(dentist), dentist.user.email, dentist.user.phone, dentist.specialization, dentist.license_number, dentist.available_days, "Active" if dentist.user.is_active else "Inactive"] for dentist in qs]


@role_required(User.Role.ADMIN, User.Role.RECEPTIONIST)
def export_pdf(request):
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="dentists.pdf"'
    buffer = BytesIO()
    SimpleDocTemplate(buffer, pagesize=A4).build([Table(export_rows(filtered_dentists(request)))])
    response.write(buffer.getvalue())
    return response


@role_required(User.Role.ADMIN, User.Role.RECEPTIONIST)
def export_excel(request):
    wb = Workbook()
    ws = wb.active
    for row in export_rows(filtered_dentists(request)):
        ws.append(row)
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="dentists.xlsx"'
    wb.save(response)
    return response
