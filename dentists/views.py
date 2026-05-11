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
    return render(request, "dentists/dentist_list.html", {
        "dentists": dentists,
        "form": form,
        "edit_form": edit_form,
        "edit_dentist": edit_dentist,
        "modal_open": modal_open,
        "edit_modal_open": edit_modal_open,
        "kpis": kpis,
    })


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
    return {
        "id": dentist.pk,
        "first_name": dentist.user.first_name,
        "last_name": dentist.user.last_name,
        "email": dentist.user.email,
        "phone": dentist.user.phone,
        "specialization": dentist.specialization,
        "license_number": dentist.license_number,
        "available_days": [day.strip() for day in dentist.available_days.split(",") if day.strip()],
        "available_from": dentist.available_from.strftime("%H:%M"),
        "available_to": dentist.available_to.strftime("%H:%M"),
        "appointment_duration": dentist.appointment_duration,
        "max_patients_per_day": dentist.max_patients_per_day,
        "break_start_time": dentist.break_start_time.strftime("%H:%M") if dentist.break_start_time else "",
        "break_end_time": dentist.break_end_time.strftime("%H:%M") if dentist.break_end_time else "",
        "is_available": dentist.is_available,
        "is_active": dentist.user.is_active,
        "display": {
            "dentist": str(dentist),
            "email": dentist.user.email,
            "phone": dentist.user.phone or "-",
            "specialization": dentist.specialization or "-",
            "license": dentist.license_number,
            "days": dentist.available_days,
            "schedule": f"{dentist.available_from:%H:%M}-{dentist.available_to:%H:%M}",
        },
    }


@role_required(User.Role.ADMIN)
def dentist_json(request, pk):
    dentist = get_object_or_404(DentistProfile.objects.select_related("user"), pk=pk)
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
@role_required(User.Role.ADMIN, User.Role.RECEPTIONIST)
def dentist_delete(request, pk):
    dentist = get_object_or_404(DentistProfile.objects.select_related("user"), pk=pk)
    dentist.user.delete()
    messages.success(request, "Dentist deleted.")
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "message": "Dentist deleted."})
    return redirect("dentists:list")


def export_rows(qs):
    return [["Dentist", "Email", "Phone", "Specialization", "License", "Available Days", "Hours", "Duration", "Daily Capacity", "Status"]] + [[str(dentist), dentist.user.email, dentist.user.phone, dentist.specialization, dentist.license_number, dentist.available_days, f"{dentist.available_from}-{dentist.available_to}", dentist.appointment_duration, dentist.max_patients_per_day, "Available" if dentist.user.is_active and dentist.is_available else "Inactive"] for dentist in qs]


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
