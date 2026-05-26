from io import BytesIO

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table

from accounts.models import User
from accounts.permissions import role_required
from appointments.models import Appointment
from .forms import DentistEditForm, DentistForm
from .models import DentistProfile


def _dashboard_base_ctx(user):
    from notifications.models import Notification
    if user.role == User.Role.RECEPTIONIST:
        return {
            "base_template": "dashboard/receptionist_base.html",
            "unread_count": Notification.objects.filter(user=user, is_read=False).count(),
        }
    return {"base_template": "dashboard/base.html"}


def filtered_dentists(request):
    qs = DentistProfile.objects.select_related("user").prefetch_related("day_schedules")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q) | Q(user__email__icontains=q) | Q(user__phone__icontains=q) | Q(license_number__icontains=q))
    if request.GET.get("specialization"):
        qs = qs.filter(specialization__icontains=request.GET["specialization"])
    if request.GET.get("availability"):
        qs = qs.filter(available_days__icontains=request.GET["availability"])
    return qs


@role_required(User.Role.ADMIN)
def dentist_list(request):
    form = DentistForm()
    edit_form = DentistEditForm()
    modal_open = False
    edit_modal_open = False
    edit_dentist = None
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
        {"label": "Available Dentists", "value": dentists.filter(user__is_active=True, is_available=True).count(), "icon": "verified_user"},
        {"label": "Specialists", "value": dentists.exclude(specialization="").count(), "icon": "medical_services"},
        {"label": "Appointments Today", "value": Appointment.objects.filter(appointment_date=today).count(), "icon": "calendar_today"},
    ]
    ctx = _dashboard_base_ctx(request.user)
    ctx.update({
        "dentists": dentists,
        "form": form,
        "edit_form": edit_form,
        "edit_dentist": edit_dentist,
        "modal_open": modal_open,
        "edit_modal_open": edit_modal_open,
        "kpis": kpis,
    })
    return render(request, "dentists/dentist_list.html", ctx)


@require_POST
@role_required(User.Role.ADMIN)
def dentist_edit(request, pk):
    dentist = get_object_or_404(DentistProfile.objects.select_related("user"), pk=pk)
    edit_form = DentistEditForm(request.POST, instance=dentist)
    if edit_form.is_valid():
        edit_form.save()
        messages.success(request, "Dentist updated successfully.")
        return redirect("dentists:list")

    dentists = filtered_dentists(request)
    today = timezone.localdate()
    kpis = [
        {"label": "Total Dentists", "value": dentists.count(), "icon": "dentistry"},
        {"label": "Available Dentists", "value": dentists.filter(user__is_active=True, is_available=True).count(), "icon": "verified_user"},
        {"label": "Specialists", "value": dentists.exclude(specialization="").count(), "icon": "medical_services"},
        {"label": "Appointments Today", "value": Appointment.objects.filter(appointment_date=today).count(), "icon": "calendar_today"},
    ]
    return render(request, "dentists/dentist_list.html", {
        "dentists": dentists,
        "form": DentistForm(),
        "edit_form": edit_form,
        "edit_dentist": dentist,
        "modal_open": False,
        "edit_modal_open": True,
        "kpis": kpis,
    })


def dentist_payload(dentist):
    day_schedules = {}
    for sched in dentist.day_schedules.all():
        day_schedules[sched.day] = {
            "start": sched.start_time.strftime("%H:%M"),
            "end": sched.end_time.strftime("%H:%M"),
            "break_start": sched.break_start.strftime("%H:%M") if sched.break_start else "",
            "break_end": sched.break_end.strftime("%H:%M") if sched.break_end else "",
        }
    working_days = list(day_schedules.keys()) if day_schedules else [
        d.strip().lower() for d in dentist.available_days.split(",") if d.strip()
    ]
    return {
        "id": dentist.pk,
        "first_name": dentist.user.first_name,
        "last_name": dentist.user.last_name,
        "email": dentist.user.email,
        "phone": dentist.user.phone,
        "specialization": dentist.specialization,
        "license_number": dentist.license_number,
        "appointment_duration": dentist.appointment_duration,
        "max_patients_per_day": dentist.max_patients_per_day,
        "is_available": dentist.is_available,
        "is_active": dentist.user.is_active,
        "day_schedules": day_schedules,
        "display": {
            "dentist": str(dentist),
            "email": dentist.user.email,
            "phone": dentist.user.phone or "-",
            "specialization": dentist.specialization or "-",
            "license": dentist.license_number,
            "days": ", ".join(d.capitalize() for d in working_days),
        },
    }


@role_required(User.Role.ADMIN)
def dentist_json(request, pk):
    dentist = get_object_or_404(DentistProfile.objects.select_related("user").prefetch_related("day_schedules"), pk=pk)
    return JsonResponse({"ok": True, "record": dentist_payload(dentist)})


@require_POST
@role_required(User.Role.ADMIN)
def dentist_update(request, pk):
    dentist = get_object_or_404(DentistProfile.objects.select_related("user"), pk=pk)
    form = DentistEditForm(request.POST, instance=dentist)
    if form.is_valid():
        dentist = form.save()
        return JsonResponse({"ok": True, "message": "Dentist updated successfully.", "record": dentist_payload(dentist)})
    return JsonResponse({"ok": False, "message": "Please correct the dentist form errors.", "errors": form.errors}, status=400)


@require_POST
@role_required(User.Role.ADMIN)
def dentist_delete(request, pk):
    dentist = get_object_or_404(DentistProfile.objects.select_related("user"), pk=pk)
    dentist.user.delete()
    messages.success(request, "Dentist deleted.")
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "message": "Dentist deleted."})
    return redirect("dentists:list")


def export_rows(qs):
    return [["Dentist", "Email", "Phone", "Specialization", "License", "Available Days", "Hours", "Duration", "Daily Capacity", "Status"]] + [[str(dentist), dentist.user.email, dentist.user.phone, dentist.specialization, dentist.license_number, dentist.available_days, f"{dentist.available_from}-{dentist.available_to}", dentist.appointment_duration, dentist.max_patients_per_day, "Available" if dentist.user.is_active and dentist.is_available else "Inactive"] for dentist in qs]


@role_required(User.Role.ADMIN)
def export_pdf(request):
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="dentists.pdf"'
    buffer = BytesIO()
    SimpleDocTemplate(buffer, pagesize=A4).build([Table(export_rows(filtered_dentists(request)))])
    response.write(buffer.getvalue())
    return response


@role_required(User.Role.ADMIN)
def export_excel(request):
    wb = Workbook()
    ws = wb.active
    for row in export_rows(filtered_dentists(request)):
        ws.append(row)
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="dentists.xlsx"'
    wb.save(response)
    return response
