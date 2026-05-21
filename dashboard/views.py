from django.contrib.auth.decorators import login_required
from django.contrib import messages
import json

from django.db import IntegrityError
from django.db.models import Count, Q, Sum
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from accounts.models import User
from accounts.permissions import get_dashboard_url_for_user, role_required
from appointments.forms import AppointmentBookingForm, AppointmentManageForm
from treatments.forms import DentistTreatmentForm
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


def _patient_ctx(user):
    from notifications.models import Notification
    return {"unread_count": Notification.objects.filter(user=user, is_read=False).count()}


def _handle_patient_booking(request, profile, success_redirect):
    from notifications.models import Notification

    booking_form = AppointmentBookingForm()
    booking_modal_open = False

    if request.method == "POST" and request.POST.get("form_type") == "book_appointment":
        booking_modal_open = True
        booking_form = AppointmentBookingForm(request.POST)
        if booking_form.is_valid():
            appt = booking_form.save(commit=False)
            appt.patient = profile
            appt.status = Appointment.Status.PENDING
            try:
                appt.save()
            except IntegrityError:
                booking_form.add_error(
                    "appointment_time",
                    "This dentist already has an appointment at the selected date and time.",
                )
            else:
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
                messages.success(request, "Appointment booked successfully and is pending approval.")
                return booking_form, booking_modal_open, redirect(success_redirect)

    return booking_form, booking_modal_open, None


@role_required(User.Role.ADMIN)
def admin_dashboard(request):
    return render(request, "dashboard/dashboard.html", admin_dashboard_context())


@role_required(User.Role.DENTIST)
def dentist_dashboard(request):
    from notifications.models import Notification
    from django.utils import timezone as tz

    dentist = get_dentist_profile(request.user)
    today = tz.localdate()
    treatment_open = False

    notifications_qs = Notification.objects.filter(user=request.user)
    unread_count = notifications_qs.filter(is_read=False).count()
    notifications = list(notifications_qs[:8])

    if not dentist:
        return render(request, "dashboard/dentist.html", {
            "dentist": None,
            "unread_count": unread_count,
            "notifications": notifications,
            "kpis": [
                {"label": "Today's Appointments", "value": 0, "icon": "event_available"},
                {"label": "Pending Appointments", "value": 0, "icon": "pending_actions"},
                {"label": "Treatments Done", "value": 0, "icon": "healing"},
                {"label": "Patients Seen", "value": 0, "icon": "groups"},
            ],
            "today_appointments": [],
            "filtered_appointments": [],
            "recent_treatments": [],
            "treatment_form": DentistTreatmentForm(dentist=None),
            "treatment_open": False,
            "today": today,
            "search": "",
            "status_filter": "",
            "date_filter": "",
            "status_choices": Appointment.Status.choices,
        })

    all_appointments = (
        Appointment.objects.filter(dentist=dentist)
        .select_related("patient__user")
    )
    today_appointments = (
        all_appointments.filter(appointment_date=today)
        .order_by("appointment_time")
    )

    today_count = today_appointments.count()
    pending_count = all_appointments.filter(status=Appointment.Status.PENDING).count()
    completed_treatments = Treatment.objects.filter(dentist=dentist).count()
    patients_seen = (
        all_appointments.filter(status=Appointment.Status.COMPLETED)
        .values("patient").distinct().count()
    )

    search = request.GET.get("q", "")
    status_filter = request.GET.get("status", "")
    date_filter = request.GET.get("date", "")

    filtered_appointments = all_appointments.order_by("-appointment_date", "-appointment_time")
    if search:
        filtered_appointments = filtered_appointments.filter(
            Q(patient__user__first_name__icontains=search)
            | Q(patient__user__last_name__icontains=search)
            | Q(reason__icontains=search)
        )
    if status_filter:
        filtered_appointments = filtered_appointments.filter(status=status_filter)
    if date_filter:
        filtered_appointments = filtered_appointments.filter(appointment_date=date_filter)

    recent_treatments = (
        Treatment.objects.filter(dentist=dentist)
        .select_related("patient__user")
        .order_by("-treatment_date")[:10]
    )

    treatment_form = DentistTreatmentForm(dentist=dentist)

    if request.method == "POST" and request.POST.get("form_type") == "treatment":
        treatment_open = True
        treatment_form = DentistTreatmentForm(request.POST, dentist=dentist)
        if treatment_form.is_valid():
            t = treatment_form.save(commit=False)
            t.dentist = dentist
            if t.appointment:
                t.patient = t.appointment.patient
            t.save()
            if t.appointment and t.appointment.status != Appointment.Status.COMPLETED:
                t.appointment.status = Appointment.Status.COMPLETED
                t.appointment.save(update_fields=["status"])
            messages.success(request, "Treatment record saved successfully.")
            return redirect("dashboard:dentist")

    return render(
        request,
        "dashboard/dentist.html",
        {
            "dentist": dentist,
            "today_appointments": today_appointments,
            "filtered_appointments": filtered_appointments[:20],
            "recent_treatments": recent_treatments,
            "treatment_form": treatment_form,
            "treatment_open": treatment_open,
            "kpis": [
                {"label": "Today's Appointments", "value": today_count, "icon": "event_available"},
                {"label": "Pending Appointments", "value": pending_count, "icon": "pending_actions"},
                {"label": "Treatments Done", "value": completed_treatments, "icon": "healing"},
                {"label": "Patients Seen", "value": patients_seen, "icon": "groups"},
            ],
            "notifications": notifications,
            "unread_count": unread_count,
            "search": search,
            "status_filter": status_filter,
            "date_filter": date_filter,
            "today": today,
            "status_choices": Appointment.Status.choices,
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


def _receptionist_ctx(user):
    from notifications.models import Notification
    from django.utils import timezone as tz

    today = tz.localdate()
    today_count = Appointment.objects.filter(appointment_date=today).count()
    pending_count = Appointment.objects.filter(status=Appointment.Status.PENDING).count()
    registered_patients = PatientProfile.objects.count()
    unpaid_count = Invoice.objects.filter(status=Invoice.Status.UNPAID).count()
    unread_count = Notification.objects.filter(user=user, is_read=False).count()
    return {
        "unread_count": unread_count,
        "kpis": [
            {"label": "Today's Appointments", "value": today_count, "icon": "event_available"},
            {"label": "Pending Requests", "value": pending_count, "icon": "pending_actions"},
            {"label": "Registered Patients", "value": registered_patients, "icon": "groups"},
            {"label": "Unpaid Invoices", "value": unpaid_count, "icon": "receipt_long"},
        ],
        "today": today,
        "status_choices": Appointment.Status.choices,
    }


@role_required(User.Role.RECEPTIONIST)
def receptionist_dashboard(request):
    from django.utils import timezone as tz

    today = tz.localdate()
    appt_open = False
    patient_open = False

    today_schedule = (
        Appointment.objects.filter(appointment_date=today)
        .select_related("patient__user", "dentist__user")
        .order_by("appointment_time")
    )
    pending_appointments = (
        Appointment.objects.filter(status=Appointment.Status.PENDING)
        .select_related("patient__user", "dentist__user")
        .order_by("appointment_date", "appointment_time")[:5]
    )
    recent_patients = (
        PatientProfile.objects.select_related("user")
        .order_by("-user__date_joined")[:6]
    )
    recent_invoices = (
        Invoice.objects
        .select_related("patient__user", "appointment")
        .order_by("-created_at")[:6]
    )

    appointment_form = AppointmentManageForm(prefix="appointment")
    patient_form = PatientRegistrationForm(prefix="patient")

    if request.method == "POST":
        form_type = request.POST.get("form_type")
        if form_type == "appointment":
            appt_open = True
            appointment_form = AppointmentManageForm(request.POST, prefix="appointment")
            if appointment_form.is_valid():
                appointment_form.save()
                messages.success(request, "Appointment created successfully.")
                return redirect("dashboard:receptionist")
        elif form_type == "patient":
            patient_open = True
            patient_form = PatientRegistrationForm(request.POST, prefix="patient")
            if patient_form.is_valid():
                patient_form.save()
                messages.success(request, "Patient registered successfully.")
                return redirect("dashboard:receptionist")

    # Appointment chart — last 6 months
    from datetime import date as _date
    chart_labels, chart_booked, chart_completed = [], [], []
    for i in range(5, -1, -1):
        m = today.month - i
        y = today.year + (m - 1) // 12
        m = ((m - 1) % 12) + 1
        mo_start = _date(y, m, 1)
        mo_end = _date(y + (m // 12), (m % 12) + 1, 1)
        qs = Appointment.objects.filter(appointment_date__gte=mo_start, appointment_date__lt=mo_end)
        chart_labels.append(mo_start.strftime("%b"))
        chart_booked.append(qs.count())
        chart_completed.append(qs.filter(status=Appointment.Status.COMPLETED).count())

    invoice_stats = Invoice.objects.aggregate(
        paid=Count("id", filter=Q(status=Invoice.Status.PAID)),
        unpaid=Count("id", filter=Q(status=Invoice.Status.UNPAID)),
        cancelled=Count("id", filter=Q(status=Invoice.Status.CANCELLED)),
    )

    ctx = _receptionist_ctx(request.user)
    ctx.update({
        "today_schedule": today_schedule,
        "pending_appointments": pending_appointments,
        "recent_patients": recent_patients,
        "recent_invoices": recent_invoices,
        "appointment_form": appointment_form,
        "patient_form": patient_form,
        "appt_open": appt_open,
        "patient_open": patient_open,
        "invoice_stats": invoice_stats,
        "appointment_chart": json.dumps({"labels": chart_labels, "booked": chart_booked, "completed": chart_completed}),
    })
    return render(request, "dashboard/receptionist.html", ctx)


@role_required(User.Role.PATIENT)
def patient_dashboard(request):
    from notifications.models import Notification
    from django.utils import timezone as tz

    profile = get_patient_profile(request.user)
    booking_form, booking_modal_open, booking_response = _handle_patient_booking(
        request,
        profile,
        "dashboard:patient",
    )
    if booking_response:
        return booking_response

    appointments = (
        Appointment.objects.filter(patient=profile)
        .select_related("dentist__user")
        .order_by("-appointment_date", "-appointment_time")[:5]
    )
    treatments = (
        Treatment.objects.filter(patient=profile)
        .select_related("dentist__user", "appointment")
        .order_by("-treatment_date")[:3]
    )
    invoices = (
        Invoice.objects.filter(patient=profile)
        .select_related("appointment")
        .order_by("-created_at")[:5]
    )

    today = tz.localdate()
    all_appts = Appointment.objects.filter(patient=profile)
    kpis = [
        {
            "label": "Upcoming",
            "value": all_appts.filter(
                appointment_date__gte=today,
                status__in=[Appointment.Status.PENDING, Appointment.Status.APPROVED],
            ).count(),
            "icon": "upcoming",
        },
        {
            "label": "Pending",
            "value": all_appts.filter(status=Appointment.Status.PENDING).count(),
            "icon": "pending_actions",
        },
        {
            "label": "Treatments",
            "value": Treatment.objects.filter(patient=profile).count(),
            "icon": "healing",
        },
        {
            "label": "Unpaid Invoices",
            "value": Invoice.objects.filter(patient=profile, status=Invoice.Status.UNPAID).count(),
            "icon": "receipt_long",
        },
    ]

    notifications_qs = Notification.objects.filter(user=request.user)
    unread_count = notifications_qs.filter(is_read=False).count()
    notifications = notifications_qs[:5]

    return render(
        request,
        "dashboard/patient.html",
        {
            "profile": profile,
            "appointments": appointments,
            "treatments": treatments,
            "invoices": invoices,
            "kpis": kpis,
            "notifications": notifications,
            "unread_count": unread_count,
            "booking_form": booking_form,
            "booking_modal_open": booking_modal_open,
        },
    )


@require_POST
@role_required(User.Role.PATIENT)
def patient_cancel_appointment(request, pk):
    profile = get_patient_profile(request.user)
    appointment = Appointment.objects.filter(pk=pk, patient=profile).first()
    if not appointment:
        messages.error(request, "Appointment not found.")
        return redirect("dashboard:patient_appointments")
    if appointment.status not in [Appointment.Status.PENDING, Appointment.Status.APPROVED]:
        messages.error(request, "This appointment cannot be cancelled.")
        return redirect("dashboard:patient_appointments")
    appointment.status = Appointment.Status.CANCELLED
    appointment.save(update_fields=["status"])
    messages.success(request, "Appointment cancelled successfully.")
    return redirect("dashboard:patient_appointments")


@role_required(User.Role.PATIENT)
def patient_appointments_page(request):
    profile = get_patient_profile(request.user)
    booking_form, booking_modal_open, booking_response = _handle_patient_booking(
        request,
        profile,
        "dashboard:patient_appointments",
    )
    if booking_response:
        return booking_response

    appointments = (
        Appointment.objects.filter(patient=profile)
        .select_related("dentist__user")
        .order_by("-appointment_date", "-appointment_time")
    )
    ctx = _patient_ctx(request.user)
    ctx.update({
        "appointments": appointments,
        "booking_form": booking_form,
        "booking_modal_open": booking_modal_open,
    })
    return render(request, "dashboard/patient/appointments.html", ctx)


@role_required(User.Role.PATIENT)
def patient_book_page(request):
    from notifications.models import Notification

    profile = get_patient_profile(request.user)
    booking_form = AppointmentBookingForm()

    if request.method == "POST":
        booking_form = AppointmentBookingForm(request.POST)
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
            messages.success(request, "Appointment booked successfully and is pending approval.")
            return redirect("dashboard:patient_appointments")

    ctx = _patient_ctx(request.user)
    ctx["booking_form"] = booking_form
    return render(request, "dashboard/patient/book.html", ctx)


@role_required(User.Role.PATIENT)
def patient_notifications_page(request):
    from notifications.models import Notification

    notifications_qs = Notification.objects.filter(user=request.user)
    unread_count = notifications_qs.filter(is_read=False).count()
    return render(request, "dashboard/patient/notifications.html", {
        "notifications": notifications_qs,
        "unread_count": unread_count,
    })


@role_required(User.Role.PATIENT)
def patient_treatments_page(request):
    profile = get_patient_profile(request.user)
    treatments = (
        Treatment.objects.filter(patient=profile)
        .select_related("dentist__user", "appointment")
        .order_by("-treatment_date")
    )
    ctx = _patient_ctx(request.user)
    ctx["treatments"] = treatments
    return render(request, "dashboard/patient/treatments.html", ctx)


@role_required(User.Role.PATIENT)
def patient_invoices_page(request):
    profile = get_patient_profile(request.user)
    invoices = (
        Invoice.objects.filter(patient=profile)
        .select_related("appointment")
        .order_by("-created_at")
    )
    ctx = _patient_ctx(request.user)
    ctx["invoices"] = invoices
    return render(request, "dashboard/patient/invoices.html", ctx)


@role_required(User.Role.RECEPTIONIST)
def receptionist_appointments_page(request):
    from django.utils import timezone as tz

    today = tz.localdate()
    appt_open = False

    today_schedule = (
        Appointment.objects.filter(appointment_date=today)
        .select_related("patient__user", "dentist__user")
        .order_by("appointment_time")
    )
    pending_appointments = (
        Appointment.objects.filter(status=Appointment.Status.PENDING)
        .select_related("patient__user", "dentist__user")
        .order_by("appointment_date", "appointment_time")
    )

    appointment_form = AppointmentManageForm(prefix="appointment")

    if request.method == "POST" and request.POST.get("form_type") == "appointment":
        appt_open = True
        appointment_form = AppointmentManageForm(request.POST, prefix="appointment")
        if appointment_form.is_valid():
            appointment_form.save()
            messages.success(request, "Appointment created successfully.")
            return redirect("dashboard:receptionist_appointments")

    ctx = _receptionist_ctx(request.user)
    ctx.update({
        "today_schedule": today_schedule,
        "pending_appointments": pending_appointments,
        "appointment_form": appointment_form,
        "appt_open": appt_open,
    })
    return render(request, "dashboard/receptionist/appointments.html", ctx)


@role_required(User.Role.RECEPTIONIST)
def receptionist_notifications_page(request):
    from notifications.models import Notification

    notifications_qs = Notification.objects.filter(user=request.user).order_by("-created_at")
    ctx = _receptionist_ctx(request.user)
    ctx["notifications"] = notifications_qs
    return render(request, "dashboard/receptionist/notifications.html", ctx)


@role_required(User.Role.RECEPTIONIST)
def receptionist_profile_page(request):
    ctx = _receptionist_ctx(request.user)
    return render(request, "dashboard/receptionist/profile.html", ctx)


@role_required(User.Role.PATIENT)
def patient_profile_page(request):
    profile = get_patient_profile(request.user)
    profile_form = PatientProfileForm(instance=profile)

    if request.method == "POST":
        if request.POST.get("remove_photo") and profile.profile_image:
            profile.profile_image.delete(save=False)
            profile.profile_image = None
            profile.save(update_fields=["profile_image"])
            messages.success(request, "Profile photo removed.")
            return redirect("dashboard:patient_profile")

        old_image = profile.profile_image.name if profile.profile_image else None
        profile_form = PatientProfileForm(request.POST, request.FILES, instance=profile)
        if profile_form.is_valid():
            if old_image and "profile_image" in request.FILES:
                from django.core.files.storage import default_storage
                if default_storage.exists(old_image):
                    default_storage.delete(old_image)
            profile_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("dashboard:patient_profile")

    ctx = _patient_ctx(request.user)
    ctx.update({"profile": profile, "profile_form": profile_form})
    return render(request, "dashboard/patient/profile.html", ctx)
