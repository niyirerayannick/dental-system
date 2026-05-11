from django.contrib.auth.decorators import login_required
from django.contrib import messages
import json

from django.db.models import Count, Q, Sum
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from accounts.models import User
from accounts.permissions import get_dashboard_url_for_user, role_required
from appointments.forms import AppointmentBookingForm, AppointmentManageForm
from appointments.models import Appointment
from billing.models import Invoice
from dentists.models import DentistProfile
from patients.forms import PatientProfileForm, PatientRegistrationForm
from patients.models import PatientProfile
from treatments.forms import TreatmentRecordForm
from treatments.models import Treatment


@login_required
def role_dashboard_redirect(request):
    return redirect(get_dashboard_url_for_user(request.user))


def admin_dashboard_context():
    revenue = Invoice.objects.filter(status=Invoice.Status.PAID).aggregate(total=Sum("amount"))["total"] or 0
    stats = [
        {"label": "Total Patients", "value": PatientProfile.objects.count(), "change": "+10%", "tone": "green", "icon": "groups"},
        {"label": "Total Appointments", "value": Appointment.objects.count(), "change": "+15%", "tone": "green", "icon": "event_available"},
        {"label": "Total Dentists", "value": DentistProfile.objects.count(), "change": "+6%", "tone": "green", "icon": "dentistry"},
        {"label": "Revenue", "value": f"${revenue:,.0f}", "change": "+12%", "tone": "green", "icon": "paid"},
        {"label": "Pending Appointments", "value": Appointment.objects.filter(status=Appointment.Status.PENDING).count(), "change": "Review", "tone": "amber", "icon": "pending_actions"},
        {"label": "Completed Treatments", "value": Treatment.objects.count(), "change": "+8%", "tone": "green", "icon": "medication"},
    ]
    invoice_stats = Invoice.objects.aggregate(
        paid=Count("id", filter=Q(status=Invoice.Status.PAID)),
        unpaid=Count("id", filter=Q(status=Invoice.Status.UNPAID)),
        cancelled=Count("id", filter=Q(status=Invoice.Status.CANCELLED)),
    )
    appointments = Appointment.objects.select_related("patient__user", "dentist__user")[:8]
    recent_patients = PatientProfile.objects.select_related("user")[:6]
    today_schedule = Appointment.objects.select_related("patient__user", "dentist__user").order_by("appointment_time")[:5]
    appointment_requests = Appointment.objects.filter(status=Appointment.Status.PENDING).select_related("patient__user", "dentist__user")[:5]

    return {
        "stats": stats,
        "invoice_stats": invoice_stats,
        "appointments": appointments,
        "recent_patients": recent_patients,
        "today_schedule": today_schedule,
        "appointment_requests": appointment_requests,
        "revenue": revenue,
        "appointment_chart": json.dumps(
            {
                "labels": ["Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct"],
                "booked": [18, 24, 26, 25, 29, 27, 31, 28, 32],
                "completed": [14, 21, 24, 22, 25, 24, 27, 25, 29],
            }
        ),
        "treatment_chart": json.dumps(
            {
                "labels": ["Root Canal", "Cleaning", "Whitening", "Extraction"],
                "values": [35, 30, 20, 15],
            }
        ),
    }


def get_patient_profile(user):
    profile, _created = PatientProfile.objects.get_or_create(user=user)
    return profile


def get_dentist_profile(user):
    return DentistProfile.objects.filter(user=user).first()


@role_required(User.Role.ADMIN)
def admin_dashboard(request):
    return render(request, "dashboard/dashboard.html", admin_dashboard_context())


@role_required(User.Role.DENTIST)
def dentist_dashboard(request):
    dentist = get_dentist_profile(request.user)
    appointments = Appointment.objects.none()
    treatment_form = TreatmentRecordForm()

    if dentist:
        appointments = Appointment.objects.filter(dentist=dentist).select_related("patient__user", "dentist__user")
        treatment_form = TreatmentRecordForm(initial={"dentist": dentist})
        treatment_form.fields["dentist"].queryset = DentistProfile.objects.filter(pk=dentist.pk)
        treatment_form.fields["appointment"].queryset = appointments.filter(status=Appointment.Status.COMPLETED)

    if request.method == "POST":
        treatment_form = TreatmentRecordForm(request.POST)
        if dentist:
            treatment_form.fields["dentist"].queryset = DentistProfile.objects.filter(pk=dentist.pk)
            treatment_form.fields["appointment"].queryset = appointments.filter(status=Appointment.Status.COMPLETED)
        if treatment_form.is_valid():
            treatment = treatment_form.save(commit=False)
            treatment.dentist = dentist
            treatment.save()
            messages.success(request, "Treatment record added.")
            return redirect("dashboard:dentist")

    return render(
        request,
        "dashboard/dentist.html",
        {
            "dentist": dentist,
            "appointments": appointments,
            "treatment_form": treatment_form,
        },
    )


@require_POST
@role_required(User.Role.DENTIST, User.Role.RECEPTIONIST)
def update_appointment_status(request, pk, status):
    allowed_statuses = {
        Appointment.Status.APPROVED,
        Appointment.Status.CANCELLED,
        Appointment.Status.COMPLETED,
    }
    redirect_url = get_dashboard_url_for_user(request.user)

    if request.user.role == User.Role.DENTIST:
        dentist = get_dentist_profile(request.user)
        appointment = Appointment.objects.filter(pk=pk, dentist=dentist).first()
    else:
        appointment = Appointment.objects.filter(pk=pk).first()

    if not appointment:
        messages.error(request, "Appointment could not be found.")
        return redirect(redirect_url)
    if status not in allowed_statuses:
        messages.error(request, "That appointment status is not allowed.")
        return redirect(redirect_url)
    if appointment.status == Appointment.Status.CANCELLED and status != Appointment.Status.CANCELLED:
        messages.error(request, "Cancelled appointments cannot be changed.")
        return redirect(redirect_url)

    if appointment.status != status:
        appointment.status = status
        appointment.save(update_fields=["status"])
        messages.success(request, f"Appointment marked as {appointment.get_status_display().lower()}.")
    else:
        messages.success(request, "Appointment status is already up to date.")

    return redirect(redirect_url)


@role_required(User.Role.RECEPTIONIST)
def receptionist_dashboard(request):
    appointment_form = AppointmentManageForm(prefix="appointment")
    patient_form = PatientRegistrationForm(prefix="patient")

    if request.method == "POST":
        form_type = request.POST.get("form_type")
        if form_type == "appointment":
            appointment_form = AppointmentManageForm(request.POST, prefix="appointment")
            if appointment_form.is_valid():
                appointment_form.save()
                messages.success(request, "Appointment saved.")
                return redirect("dashboard:receptionist")
            messages.error(request, "Please correct the appointment form errors.")
        elif form_type == "patient":
            patient_form = PatientRegistrationForm(request.POST, prefix="patient")
            if patient_form.is_valid():
                patient_form.save()
                messages.success(request, "Patient registered.")
                return redirect("dashboard:receptionist")
            messages.error(request, "Please correct the patient registration errors.")

    appointments = Appointment.objects.select_related("patient__user", "dentist__user")[:20]
    invoices = Invoice.objects.select_related("patient__user", "appointment")[:12]

    return render(
        request,
        "dashboard/receptionist.html",
        {
            "appointment_form": appointment_form,
            "patient_form": patient_form,
            "appointments": appointments,
            "invoices": invoices,
        },
    )


@role_required(User.Role.PATIENT)
def patient_dashboard(request):
    from notifications.models import Notification
    from django.utils import timezone as tz

    profile = get_patient_profile(request.user)
    profile_form = PatientProfileForm(instance=profile, prefix="profile")
    booking_form = AppointmentBookingForm(prefix="booking")
    booking_open = False
    profile_open = False

    appointments = (
        Appointment.objects.filter(patient=profile)
        .select_related("dentist__user")
        .order_by("-appointment_date", "-appointment_time")
    )
    treatments = (
        Treatment.objects.filter(patient=profile)
        .select_related("dentist__user", "appointment")
        .order_by("-treatment_date")
    )
    invoices = (
        Invoice.objects.filter(patient=profile)
        .select_related("appointment")
        .order_by("-created_at")
    )

    today = tz.localdate()
    kpis = [
        {
            "label": "Upcoming",
            "value": appointments.filter(
                appointment_date__gte=today,
                status__in=[Appointment.Status.PENDING, Appointment.Status.APPROVED],
            ).count(),
            "icon": "upcoming",
        },
        {
            "label": "Pending",
            "value": appointments.filter(status=Appointment.Status.PENDING).count(),
            "icon": "pending_actions",
        },
        {
            "label": "Treatments",
            "value": treatments.count(),
            "icon": "healing",
        },
        {
            "label": "Unpaid Invoices",
            "value": invoices.filter(status=Invoice.Status.UNPAID).count(),
            "icon": "receipt_long",
        },
    ]

    notifications_qs = Notification.objects.filter(user=request.user)
    unread_count = notifications_qs.filter(is_read=False).count()
    notifications = notifications_qs[:10]

    if request.method == "POST":
        form_type = request.POST.get("form_type")
        if form_type == "profile":
            profile_open = True
            profile_form = PatientProfileForm(request.POST, instance=profile, prefix="profile")
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Profile updated successfully.")
                return redirect("dashboard:patient")
        elif form_type == "booking":
            booking_open = True
            booking_form = AppointmentBookingForm(request.POST, prefix="booking")
            if booking_form.is_valid():
                appt = booking_form.save(commit=False)
                appt.patient = profile
                appt.status = Appointment.Status.PENDING
                appt.save()
                Notification.objects.create(
                    user=request.user,
                    title="Appointment Requested",
                    message=(
                        f"Your appointment with {appt.dentist} on "
                        f"{appt.appointment_date} at {appt.appointment_time:%H:%M} "
                        "has been submitted and is pending approval."
                    ),
                    notification_type=Notification.Type.APPOINTMENT,
                )
                messages.success(request, "Appointment request submitted successfully.")
                return redirect("dashboard:patient")

    return render(
        request,
        "dashboard/patient.html",
        {
            "profile": profile,
            "profile_form": profile_form,
            "booking_form": booking_form,
            "booking_open": booking_open,
            "profile_open": profile_open,
            "appointments": appointments,
            "treatments": treatments,
            "invoices": invoices,
            "kpis": kpis,
            "notifications": notifications,
            "unread_count": unread_count,
        },
    )


@require_POST
@role_required(User.Role.PATIENT)
def patient_cancel_appointment(request, pk):
    profile = get_patient_profile(request.user)
    appointment = Appointment.objects.filter(pk=pk, patient=profile).first()
    if not appointment:
        messages.error(request, "Appointment not found.")
        return redirect("dashboard:patient")
    if appointment.status not in [Appointment.Status.PENDING, Appointment.Status.APPROVED]:
        messages.error(request, "This appointment cannot be cancelled.")
        return redirect("dashboard:patient")
    appointment.status = Appointment.Status.CANCELLED
    appointment.save(update_fields=["status"])
    messages.success(request, "Appointment cancelled successfully.")
    return redirect("dashboard:patient")
