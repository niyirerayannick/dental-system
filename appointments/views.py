from io import BytesIO

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table

from accounts.models import User
from accounts.permissions import role_required
from notifications.notifiers import notify_appointment_created, notify_appointment_status_change
from .forms import AppointmentManageForm, available_dentists
from .models import Appointment
from .services import availability_summary, booked_count, booked_times, generate_time_slots, is_fully_booked


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
            appointment = form.save()
            notify_appointment_created(appointment)
            messages.success(request, "Appointment booked successfully and is pending approval.")
            return redirect("appointments:list")
        messages.error(request, "Please correct the appointment form errors.")
    appointments = filtered_appointments(request)
    kpis = [
        {"label": "Total Appointments", "value": appointments.count(), "icon": "event_available"},
        {"label": "Pending Appointments", "value": appointments.filter(status=Appointment.Status.PENDING).count(), "icon": "pending_actions"},
        {"label": "Approved Appointments", "value": appointments.filter(status=Appointment.Status.APPROVED).count(), "icon": "task_alt"},
        {"label": "Completed Appointments", "value": appointments.filter(status=Appointment.Status.COMPLETED).count(), "icon": "check_circle"},
    ]
    return render(request, "appointments/appointment_list.html", {"appointments": appointments, "form": form, "modal_open": modal_open, "kpis": kpis, "status_choices": Appointment.Status.choices, "dentists": available_dentists()})


@role_required(User.Role.ADMIN, User.Role.DENTIST, User.Role.RECEPTIONIST, User.Role.PATIENT)
def dentist_availability_api(request, dentist_id):
    dentist = get_object_or_404(available_dentists(), pk=dentist_id)
    return JsonResponse(availability_summary(dentist))


@role_required(User.Role.ADMIN, User.Role.DENTIST, User.Role.RECEPTIONIST, User.Role.PATIENT)
def available_slots_api(request):
    dentist_id = request.GET.get("dentist_id")
    date_value = parse_date(request.GET.get("date", ""))
    if not dentist_id or not date_value:
        return JsonResponse({"error": "Select a dentist and appointment date."}, status=400)

    dentist = get_object_or_404(available_dentists(), pk=dentist_id)
    booked = sorted(time_value.strftime("%H:%M") for time_value in booked_times(dentist, date_value))
    return JsonResponse({
        "available_slots": generate_time_slots(dentist, date_value),
        "booked_slots": booked,
        "is_fully_booked": is_fully_booked(dentist, date_value),
        "max_patients_per_day": dentist.max_patients_per_day,
        "booked_count": booked_count(dentist, date_value),
    })


def appointment_payload(appointment):
    return {
        "id": appointment.pk,
        "patient": appointment.patient_id,
        "dentist": appointment.dentist_id,
        "appointment_date": appointment.appointment_date.isoformat(),
        "appointment_time": appointment.appointment_time.strftime("%H:%M"),
        "reason": appointment.reason,
        "status": appointment.status,
        "notes": appointment.notes,
        "display": {
            "patient": str(appointment.patient),
            "dentist": str(appointment.dentist),
            "date": appointment.appointment_date.isoformat(),
            "time": appointment.appointment_time.strftime("%H:%M"),
            "reason": appointment.reason or "-",
            "status": appointment.get_status_display(),
        },
    }


@role_required(User.Role.ADMIN, User.Role.DENTIST, User.Role.RECEPTIONIST)
def appointment_json(request, pk):
    appointment = get_object_or_404(Appointment.objects.select_related("patient__user", "dentist__user"), pk=pk)
    return JsonResponse({"ok": True, "record": appointment_payload(appointment)})


@require_POST
@role_required(User.Role.ADMIN, User.Role.RECEPTIONIST)
def appointment_update(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    old_status = appointment.status
    form = AppointmentManageForm(request.POST, instance=appointment)
    if form.is_valid():
        appointment = form.save()
        notify_appointment_status_change(appointment, old_status=old_status)
        return JsonResponse({"ok": True, "message": "Appointment updated successfully.", "record": appointment_payload(appointment)})
    return JsonResponse({"ok": False, "message": "Please correct the appointment form errors.", "errors": form.errors}, status=400)


@require_POST
@role_required(User.Role.ADMIN, User.Role.DENTIST, User.Role.RECEPTIONIST)
def appointment_status(request, pk, status):
    appointment = get_object_or_404(Appointment, pk=pk)
    if status in Appointment.Status.values:
        old_status = appointment.status
        appointment.status = status
        appointment.save(update_fields=["status"])
        notify_appointment_status_change(appointment, old_status=old_status)
        messages.success(request, "Appointment status updated.")
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "message": "Appointment status updated.", "record": appointment_payload(appointment)})
    return redirect("appointments:list")


@require_POST
@role_required(User.Role.ADMIN, User.Role.RECEPTIONIST)
def appointment_delete(request, pk):
    get_object_or_404(Appointment, pk=pk).delete()
    messages.success(request, "Appointment deleted.")
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "message": "Appointment deleted."})
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
