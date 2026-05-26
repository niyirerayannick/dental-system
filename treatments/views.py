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
from dentists.models import DentistProfile
from notifications.notifiers import notify_service_completed
from patients.models import PatientProfile
from .forms import TreatmentRecordForm
from .models import Treatment


def filtered_treatments(request):
    qs = Treatment.objects.select_related("patient__user", "dentist__user", "appointment")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(patient__user__first_name__icontains=q) | Q(patient__user__last_name__icontains=q) | Q(dentist__user__last_name__icontains=q) | Q(diagnosis__icontains=q) | Q(prescription__icontains=q))
    if request.GET.get("dentist"):
        qs = qs.filter(dentist_id=request.GET["dentist"])
    if request.GET.get("patient"):
        qs = qs.filter(patient_id=request.GET["patient"])
    if request.GET.get("date"):
        qs = qs.filter(treatment_date=request.GET["date"])
    return qs


@role_required(User.Role.ADMIN, User.Role.DENTIST, User.Role.RECEPTIONIST)
def treatment_list(request):
    form = TreatmentRecordForm()
    modal_open = False
    if request.method == "POST":
        form = TreatmentRecordForm(request.POST)
        modal_open = True
        if form.is_valid():
            treatment = form.save()
            if treatment.appointment:
                notify_service_completed(treatment.appointment)
            messages.success(request, "Treatment saved successfully.")
            return redirect("treatments:list")
    treatments = filtered_treatments(request)
    month_start = timezone.localdate().replace(day=1)
    kpis = [
        {"label": "Total Treatments", "value": treatments.count(), "icon": "healing"},
        {"label": "Treatments This Month", "value": treatments.filter(treatment_date__gte=month_start).count(), "icon": "calendar_month"},
        {"label": "Patients Treated", "value": treatments.values("patient").distinct().count(), "icon": "groups"},
        {"label": "Prescriptions Given", "value": treatments.exclude(prescription="").count(), "icon": "medication"},
    ]
    return render(request, "treatments/treatment_list.html", {"treatments": treatments, "form": form, "modal_open": modal_open, "kpis": kpis, "dentists": DentistProfile.objects.select_related("user"), "patients": PatientProfile.objects.select_related("user")})


@require_POST
@role_required(User.Role.ADMIN, User.Role.DENTIST, User.Role.RECEPTIONIST)
def treatment_delete(request, pk):
    treatment = get_object_or_404(Treatment, pk=pk)
    if request.user.role == User.Role.DENTIST:
        dentist = DentistProfile.objects.filter(user=request.user).first()
        if treatment.dentist_id != getattr(dentist, "pk", None):
            return JsonResponse({"ok": False, "message": "You do not have permission to delete this treatment."}, status=403)
    treatment.delete()
    messages.success(request, "Treatment deleted.")
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "message": "Treatment deleted."})
    return redirect("treatments:list")


def can_manage_treatment(user, treatment):
    if user.role in {User.Role.ADMIN, User.Role.RECEPTIONIST}:
        return True
    if user.role == User.Role.DENTIST:
        dentist = DentistProfile.objects.filter(user=user).first()
        return treatment.dentist_id == getattr(dentist, "pk", None)
    return False


def treatment_payload(treatment):
    return {
        "id": treatment.pk,
        "patient": treatment.patient_id,
        "dentist": treatment.dentist_id,
        "appointment": treatment.appointment_id or "",
        "diagnosis": treatment.diagnosis,
        "treatment_plan": treatment.treatment_plan,
        "prescription": treatment.prescription,
        "treatment_date": treatment.treatment_date.isoformat(),
        "display": {
            "patient": str(treatment.patient),
            "dentist": str(treatment.dentist),
            "appointment": str(treatment.appointment or "-"),
            "diagnosis": treatment.diagnosis[:40],
            "date": treatment.treatment_date.isoformat(),
            "prescription": treatment.prescription[:30] if treatment.prescription else "-",
        },
    }


@role_required(User.Role.ADMIN, User.Role.DENTIST, User.Role.RECEPTIONIST)
def treatment_json(request, pk):
    treatment = get_object_or_404(Treatment.objects.select_related("patient__user", "dentist__user", "appointment"), pk=pk)
    if not can_manage_treatment(request.user, treatment):
        return JsonResponse({"ok": False, "message": "Permission denied."}, status=403)
    return JsonResponse({"ok": True, "record": treatment_payload(treatment)})


@require_POST
@role_required(User.Role.ADMIN, User.Role.DENTIST, User.Role.RECEPTIONIST)
def treatment_update(request, pk):
    treatment = get_object_or_404(Treatment, pk=pk)
    if not can_manage_treatment(request.user, treatment):
        return JsonResponse({"ok": False, "message": "Permission denied."}, status=403)
    form = TreatmentRecordForm(request.POST, instance=treatment)
    if form.is_valid():
        treatment = form.save()
        if treatment.appointment:
            notify_service_completed(treatment.appointment)
        return JsonResponse({"ok": True, "message": "Treatment updated successfully.", "record": treatment_payload(treatment)})
    return JsonResponse({"ok": False, "message": "Please correct the treatment form errors.", "errors": form.errors}, status=400)


def export_rows(qs):
    return [["Patient", "Dentist", "Appointment", "Diagnosis", "Treatment Date", "Prescription"]] + [[str(t.patient), str(t.dentist), str(t.appointment or "-"), t.diagnosis, t.treatment_date, t.prescription] for t in qs]


@role_required(User.Role.ADMIN, User.Role.RECEPTIONIST)
def export_pdf(request):
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="treatments.pdf"'
    buffer = BytesIO()
    SimpleDocTemplate(buffer, pagesize=A4).build([Table(export_rows(filtered_treatments(request)))])
    response.write(buffer.getvalue())
    return response


@role_required(User.Role.ADMIN, User.Role.RECEPTIONIST)
def export_excel(request):
    wb = Workbook()
    ws = wb.active
    for row in export_rows(filtered_treatments(request)):
        ws.append(row)
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="treatments.xlsx"'
    wb.save(response)
    return response
