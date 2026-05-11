from io import BytesIO

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table

from accounts.models import User
from accounts.permissions import role_required
from dentists.models import DentistProfile
from .forms import AppointmentManageForm
from .models import Appointment


def filtered_appointments(request):
    qs = Appointment.objects.select_related("patient__user", "dentist__user")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(patient__user__first_name__icontains=q) | Q(patient__user__last_name__icontains=q) | Q(dentist__user__last_name__icontains=q) | Q(reason__icontains=q))
    if request.GET.get("status"):
        qs = qs.filter(status=request.GET["status"])
    if request.GET.get("dentist"):
        qs = qs.filter(dentist_id=request.GET["dentist"])
    if request.GET.get("date"):
        qs = qs.filter(appointment_date=request.GET["date"])
    return qs


@role_required(User.Role.ADMIN, User.Role.DENTIST, User.Role.RECEPTIONIST)
def appointment_list(request):
    form = AppointmentManageForm()
    modal_open = False
    if request.method == "POST":
        form = AppointmentManageForm(request.POST)
        modal_open = True
        if form.is_valid():
            form.save()
            messages.success(request, "Appointment saved successfully.")
            return redirect("appointments:list")
        messages.error(request, "Please correct the appointment form errors.")
    appointments = filtered_appointments(request)
    kpis = [
        {"label": "Total Appointments", "value": appointments.count(), "icon": "event_available"},
        {"label": "Pending Appointments", "value": appointments.filter(status=Appointment.Status.PENDING).count(), "icon": "pending_actions"},
        {"label": "Approved Appointments", "value": appointments.filter(status=Appointment.Status.APPROVED).count(), "icon": "task_alt"},
        {"label": "Completed Appointments", "value": appointments.filter(status=Appointment.Status.COMPLETED).count(), "icon": "check_circle"},
    ]
    return render(request, "appointments/appointment_list.html", {"appointments": appointments, "form": form, "modal_open": modal_open, "kpis": kpis, "status_choices": Appointment.Status.choices, "dentists": DentistProfile.objects.select_related("user")})


@require_POST
@role_required(User.Role.ADMIN, User.Role.DENTIST, User.Role.RECEPTIONIST)
def appointment_status(request, pk, status):
    appointment = get_object_or_404(Appointment, pk=pk)
    if status in Appointment.Status.values:
        appointment.status = status
        appointment.save(update_fields=["status"])
        messages.success(request, "Appointment status updated.")
    return redirect("appointments:list")


@require_POST
@role_required(User.Role.ADMIN, User.Role.RECEPTIONIST)
def appointment_delete(request, pk):
    get_object_or_404(Appointment, pk=pk).delete()
    messages.success(request, "Appointment deleted.")
    return redirect("appointments:list")


def export_rows(qs):
    return [["Patient", "Dentist", "Date", "Time", "Reason", "Status"]] + [[str(a.patient), str(a.dentist), a.appointment_date, a.appointment_time, a.reason, a.get_status_display()] for a in qs]


@role_required(User.Role.ADMIN, User.Role.RECEPTIONIST)
def export_pdf(request):
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="appointments.pdf"'
    buffer = BytesIO()
    SimpleDocTemplate(buffer, pagesize=A4).build([Table(export_rows(filtered_appointments(request)))])
    response.write(buffer.getvalue())
    return response


@role_required(User.Role.ADMIN, User.Role.RECEPTIONIST)
def export_excel(request):
    wb = Workbook()
    ws = wb.active
    for row in export_rows(filtered_appointments(request)):
        ws.append(row)
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="appointments.xlsx"'
    wb.save(response)
    return response
