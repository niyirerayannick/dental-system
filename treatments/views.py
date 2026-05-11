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
from dentists.models import DentistProfile
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


@role_required(User.Role.ADMIN, User.Role.DENTIST, User.Role.RECEPTIONIST, User.Role.PATIENT)
def treatment_list(request):
    form = TreatmentRecordForm()
    modal_open = False
    if request.method == "POST":
        form = TreatmentRecordForm(request.POST)
        modal_open = True
        if form.is_valid():
            form.save()
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
    get_object_or_404(Treatment, pk=pk).delete()
    messages.success(request, "Treatment deleted.")
    return redirect("treatments:list")


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
