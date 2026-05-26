from django.contrib.auth.decorators import login_required
from django.contrib import messages
import json

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import User
from accounts.forms import DashboardUserCreateForm, DashboardUserPasswordResetForm, DashboardUserUpdateForm
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
from notifications.notifiers import (
    notify_appointment_created,
    notify_appointment_status_change,
    notify_patient_created,
    notify_service_completed,
)


@login_required
def role_dashboard_redirect(request):
    return redirect(get_dashboard_url_for_user(request.user))


def admin_dashboard_context():
    from django.utils import timezone as tz
    from followups.models import FollowUp

    today = tz.localdate()
    pending = Appointment.objects.filter(status=Appointment.Status.PENDING).count()
    confirmed = Appointment.objects.filter(status=Appointment.Status.APPROVED).count()
    today_count = Appointment.objects.filter(appointment_date=today).count()
    missed = Appointment.objects.filter(
        appointment_date__lt=today,
        status=Appointment.Status.PENDING,
    ).count()
    followups_today = FollowUp.objects.filter(
        followup_date=today, status=FollowUp.Status.PENDING
    ).count()

    stats = [
        {"label": "Total Patients", "value": PatientProfile.objects.count(), "change": "+10%", "tone": "green", "icon": "groups"},
        {"label": "Today's Appointments", "value": today_count, "change": "Today", "tone": "green", "icon": "event_available"},
        {"label": "Total Dentists", "value": DentistProfile.objects.count(), "change": "Active", "tone": "green", "icon": "dentistry"},
        {"label": "Pending Approvals", "value": pending, "change": "Review", "tone": "amber", "icon": "pending_actions"},
        {"label": "Confirmed Appointments", "value": confirmed, "change": "Approved", "tone": "green", "icon": "task_alt"},
        {"label": "Follow-ups Today", "value": followups_today, "change": "Due", "tone": "amber", "icon": "next_plan"},
    ]

    appointments = Appointment.objects.select_related("patient__user", "dentist__user").order_by("-appointment_date")[:8]
    recent_patients = PatientProfile.objects.select_related("user")[:6]
    today_schedule = Appointment.objects.filter(appointment_date=today).select_related("patient__user", "dentist__user").order_by("appointment_time")[:8]
    appointment_requests = Appointment.objects.filter(status=Appointment.Status.PENDING).select_related("patient__user", "dentist__user")[:5]

    # Real chart data — last 6 months
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

    # Status breakdown for donut chart
    appt_status = Appointment.objects.aggregate(
        pending=Count("id", filter=Q(status=Appointment.Status.PENDING)),
        approved=Count("id", filter=Q(status=Appointment.Status.APPROVED)),
        completed=Count("id", filter=Q(status=Appointment.Status.COMPLETED)),
        cancelled=Count("id", filter=Q(status=Appointment.Status.CANCELLED)),
    )

    return {
        "stats": stats,
        "appointments": appointments,
        "recent_patients": recent_patients,
        "today_schedule": today_schedule,
        "appointment_requests": appointment_requests,
        "today": today,
        "missed_count": missed,
        "appt_status": appt_status,
        "appointment_chart": json.dumps({"labels": chart_labels, "booked": chart_booked, "completed": chart_completed}),
        "status_chart": json.dumps({
            "labels": ["Pending", "Confirmed", "Completed", "Cancelled"],
            "values": [
                appt_status["pending"],
                appt_status["approved"],
                appt_status["completed"],
                appt_status["cancelled"],
            ],
        }),
    }


def get_patient_profile(user):
    profile, _created = PatientProfile.objects.get_or_create(user=user)
    return profile


def get_dentist_profile(user):
    return DentistProfile.objects.filter(user=user).first()


def ensure_role_profile(user):
    if user.role == User.Role.PATIENT:
        PatientProfile.objects.get_or_create(user=user)
    elif user.role == User.Role.DENTIST:
        DentistProfile.ensure_for_user(user)


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
                notify_appointment_created(appt)
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


@role_required(User.Role.ADMIN)
def admin_users(request):
    search = request.GET.get("q", "").strip()
    role_filter = request.GET.get("role", "").strip()
    users = User.objects.order_by("last_name", "first_name", "phone")

    if search:
        users = users.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
            | Q(phone__icontains=search)
        )
    if role_filter:
        users = users.filter(role=role_filter)

    return render(
        request,
        "dashboard/admin_users.html",
        {
            "users": users,
            "role_choices": User.Role.choices,
            "search": search,
            "role_filter": role_filter,
        },
    )


@role_required(User.Role.ADMIN)
def admin_user_add(request):
    create_form = DashboardUserCreateForm()
    if request.method == "POST":
        create_form = DashboardUserCreateForm(request.POST)
        if create_form.is_valid():
            user = create_form.save()
            ensure_role_profile(user)
            messages.success(request, f"{user.full_name or user.phone} was added successfully.")
            return redirect("dashboard:admin_users")

    return render(
        request,
        "dashboard/admin_user_add.html",
        {"form": create_form},
    )


@role_required(User.Role.ADMIN)
def admin_user_edit(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    form = DashboardUserUpdateForm(instance=user_obj)

    if request.method == "POST":
        form = DashboardUserUpdateForm(request.POST, instance=user_obj)
        if form.is_valid():
            user_obj = form.save()
            ensure_role_profile(user_obj)
            messages.success(request, "User information updated.")
            return redirect("dashboard:admin_users")

    return render(request, "dashboard/admin_user_edit.html", {"managed_user": user_obj, "form": form})


@role_required(User.Role.ADMIN)
def admin_user_detail(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    patient_profile = PatientProfile.objects.filter(user=user_obj).first()
    dentist_profile = DentistProfile.objects.filter(user=user_obj).first()
    return render(
        request,
        "dashboard/admin_user_detail.html",
        {
            "managed_user": user_obj,
            "patient_profile": patient_profile,
            "dentist_profile": dentist_profile,
        },
    )


@role_required(User.Role.ADMIN)
def admin_user_delete(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if user_obj.pk == request.user.pk:
        messages.error(request, "You cannot delete your own account while you are logged in.")
        return redirect("dashboard:admin_users")

    if request.method == "POST":
        label = user_obj.full_name or user_obj.phone
        user_obj.delete()
        messages.success(request, f"{label} was deleted.")
        return redirect("dashboard:admin_users")

    return render(request, "dashboard/admin_user_delete.html", {"managed_user": user_obj})


@role_required(User.Role.ADMIN)
def admin_user_reset_password(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    form = DashboardUserPasswordResetForm(user_obj)

    if request.method == "POST":
        form = DashboardUserPasswordResetForm(user_obj, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "User password reset successfully.")
            return redirect("dashboard:admin_users")

    return render(request, "dashboard/admin_user_reset_password.html", {"managed_user": user_obj, "form": form})


@role_required(User.Role.DENTIST)
def dentist_dashboard(request):
    from notifications.models import Notification
    from django.utils import timezone as tz
    from datetime import date as _date
    from ask_doctor.models import DoctorConversation, DoctorMessage
    from followups.models import FollowUp

    dentist = get_dentist_profile(request.user)
    today = tz.localdate()
    treatment_open = False

    notifications_qs = Notification.objects.filter(user=request.user)
    unread_count = notifications_qs.filter(is_read=False).count()
    notifications = list(notifications_qs[:8])

    dentist_conversations = DoctorConversation.objects.filter(
        Q(assigned_doctor=request.user)
        | Q(
            assigned_doctor__isnull=True,
            status__in=[DoctorConversation.Status.OPEN, DoctorConversation.Status.PENDING],
        )
    ).select_related("patient", "assigned_doctor").prefetch_related("messages")
    recent_ask_messages = (
        DoctorMessage.objects.filter(conversation__in=dentist_conversations)
        .select_related("conversation__patient", "sender")
        .order_by("-created_at")[:5]
    )
    followup_queue = (
        FollowUp.objects.filter(assigned_to=request.user)
        .select_related("patient__user", "appointment")
        .filter(status__in=[FollowUp.Status.PENDING, FollowUp.Status.CONTACTED])
        .order_by("followup_date")[:6]
    )
    followups_due = FollowUp.objects.filter(
        assigned_to=request.user,
        followup_date__lte=today,
        status__in=[FollowUp.Status.PENDING, FollowUp.Status.CONTACTED],
    ).count()

    if not dentist:
        return render(request, "dashboard/dentist.html", {
            "dentist": None,
            "unread_count": unread_count,
            "notifications": notifications,
            "stats": [
                {"label": "My Appointments Today", "value": 0, "change": "Today", "tone": "green", "icon": "event_available"},
                {"label": "Pending Appointments", "value": 0, "change": "Review", "tone": "amber", "icon": "pending_actions"},
                {"label": "Completed Appointments", "value": 0, "change": "Done", "tone": "green", "icon": "task_alt"},
                {"label": "Follow-ups Due", "value": followups_due, "change": "Due", "tone": "amber", "icon": "next_plan"},
                {"label": "Ask Doctor Conversations", "value": dentist_conversations.count(), "change": "Inbox", "tone": "green", "icon": "mark_unread_chat_alt"},
                {"label": "Notification Summary", "value": unread_count, "change": "Unread", "tone": "amber" if unread_count else "green", "icon": "notifications"},
            ],
            "today_appointments": [],
            "filtered_appointments": [],
            "recent_patients": [],
            "recent_ask_messages": recent_ask_messages,
            "followup_queue": followup_queue,
            "treatment_form": DentistTreatmentForm(dentist=None),
            "treatment_open": False,
            "today": today,
            "search": "",
            "status_filter": "",
            "date_filter": "",
            "status_choices": Appointment.Status.choices,
            "appointment_chart": json.dumps({"labels": [], "booked": [], "completed": []}),
            "status_chart": json.dumps({"labels": ["Pending", "Confirmed", "Completed", "Cancelled"], "values": [0, 0, 0, 0]}),
            "appt_status": {"pending": 0, "approved": 0, "completed": 0, "cancelled": 0},
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
    completed_count = all_appointments.filter(status=Appointment.Status.COMPLETED).count()
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

    recent_patients = (
        PatientProfile.objects.filter(appointments__dentist=dentist)
        .select_related("user")
        .distinct()
        .order_by("-appointments__appointment_date")[:6]
    )

    chart_labels, chart_booked, chart_completed = [], [], []
    for i in range(5, -1, -1):
        month = today.month - i
        year = today.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1
        month_start = _date(year, month, 1)
        month_end = _date(year + (month // 12), (month % 12) + 1, 1)
        month_qs = all_appointments.filter(appointment_date__gte=month_start, appointment_date__lt=month_end)
        chart_labels.append(month_start.strftime("%b"))
        chart_booked.append(month_qs.count())
        chart_completed.append(month_qs.filter(status=Appointment.Status.COMPLETED).count())

    appt_status = all_appointments.aggregate(
        pending=Count("id", filter=Q(status=Appointment.Status.PENDING)),
        approved=Count("id", filter=Q(status=Appointment.Status.APPROVED)),
        completed=Count("id", filter=Q(status=Appointment.Status.COMPLETED)),
        cancelled=Count("id", filter=Q(status=Appointment.Status.CANCELLED)),
    )

    return render(
        request,
        "dashboard/dentist.html",
        {
            "dentist": dentist,
            "today_appointments": today_appointments,
            "filtered_appointments": filtered_appointments[:20],
            "recent_patients": recent_patients,
            "recent_ask_messages": recent_ask_messages,
            "followup_queue": followup_queue,
            "stats": [
                {"label": "My Appointments Today", "value": today_count, "change": "Today", "tone": "green", "icon": "event_available"},
                {"label": "Pending Appointments", "value": pending_count, "change": "Review", "tone": "amber", "icon": "pending_actions"},
                {"label": "Completed Appointments", "value": completed_count, "change": "Done", "tone": "green", "icon": "task_alt"},
                {"label": "Follow-ups Due", "value": followups_due, "change": "Due", "tone": "amber", "icon": "next_plan"},
                {"label": "Ask Doctor Conversations", "value": dentist_conversations.count(), "change": "Inbox", "tone": "green", "icon": "mark_unread_chat_alt"},
                {"label": "Notification Summary", "value": unread_count, "change": "Unread", "tone": "amber" if unread_count else "green", "icon": "notifications"},
            ],
            "notifications": notifications,
            "unread_count": unread_count,
            "search": search,
            "status_filter": status_filter,
            "date_filter": date_filter,
            "today": today,
            "status_choices": Appointment.Status.choices,
            "appointment_chart": json.dumps({"labels": chart_labels, "booked": chart_booked, "completed": chart_completed}),
            "status_chart": json.dumps({
                "labels": ["Pending", "Confirmed", "Completed", "Cancelled"],
                "values": [
                    appt_status["pending"],
                    appt_status["approved"],
                    appt_status["completed"],
                    appt_status["cancelled"],
                ],
            }),
            "appt_status": appt_status,
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
        old_status = appointment.status
        appointment.status = status
        appointment.save(update_fields=["status"])
        notify_appointment_status_change(appointment, old_status=old_status)
        messages.success(request, f"Appointment marked as {appointment.get_status_display().lower()}.")
    else:
        messages.success(request, "Appointment status is already up to date.")

    return redirect(redirect_url)


def _receptionist_ctx(user):
    from notifications.models import Notification
    from followups.models import FollowUp
    from django.utils import timezone as tz

    today = tz.localdate()
    today_count = Appointment.objects.filter(appointment_date=today).count()
    pending_count = Appointment.objects.filter(status=Appointment.Status.PENDING).count()
    confirmed_count = Appointment.objects.filter(status=Appointment.Status.APPROVED).count()
    followups_due = FollowUp.objects.filter(followup_date=today, status=FollowUp.Status.PENDING).count()
    unread_count = Notification.objects.filter(user=user, is_read=False).count()
    return {
        "unread_count": unread_count,
        "kpis": [
            {"label": "Today's Appointments", "value": today_count, "icon": "event_available"},
            {"label": "Pending Requests", "value": pending_count, "icon": "pending_actions"},
            {"label": "Confirmed", "value": confirmed_count, "icon": "task_alt"},
            {"label": "Follow-ups Due", "value": followups_due, "icon": "next_plan"},
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
    from followups.models import FollowUp

    recent_followups = (
        FollowUp.objects
        .select_related("patient__user", "assigned_to")
        .filter(status__in=[FollowUp.Status.PENDING, FollowUp.Status.CONTACTED])
        .order_by("followup_date")[:5]
    )

    appointment_form = AppointmentManageForm(prefix="appointment")
    patient_form = PatientRegistrationForm(prefix="patient")

    if request.method == "POST":
        form_type = request.POST.get("form_type")
        if form_type == "appointment":
            appt_open = True
            appointment_form = AppointmentManageForm(request.POST, prefix="appointment")
            if appointment_form.is_valid():
                appointment = appointment_form.save()
                notify_appointment_created(appointment)
                messages.success(request, "Appointment created successfully.")
                return redirect("dashboard:receptionist")
        elif form_type == "patient":
            patient_open = True
            patient_form = PatientRegistrationForm(request.POST, prefix="patient")
            if patient_form.is_valid():
                user = patient_form.save()
                notify_patient_created(user.patient_profile)
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

    # Appointment status breakdown
    appt_status = Appointment.objects.aggregate(
        pending=Count("id", filter=Q(status=Appointment.Status.PENDING)),
        approved=Count("id", filter=Q(status=Appointment.Status.APPROVED)),
        completed=Count("id", filter=Q(status=Appointment.Status.COMPLETED)),
        cancelled=Count("id", filter=Q(status=Appointment.Status.CANCELLED)),
    )

    ctx = _receptionist_ctx(request.user)
    ctx.update({
        "today_schedule": today_schedule,
        "pending_appointments": pending_appointments,
        "recent_patients": recent_patients,
        "recent_followups": recent_followups,
        "appointment_form": appointment_form,
        "patient_form": patient_form,
        "appt_open": appt_open,
        "patient_open": patient_open,
        "appt_status": appt_status,
        "appointment_chart": json.dumps({"labels": chart_labels, "booked": chart_booked, "completed": chart_completed}),
        "status_chart": json.dumps({
            "labels": ["Pending", "Confirmed", "Completed", "Cancelled"],
            "values": [appt_status["pending"], appt_status["approved"], appt_status["completed"], appt_status["cancelled"]],
        }),
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

    initial = {}
    dentist_id = request.GET.get("dentist")
    service_id = request.GET.get("service")
    if dentist_id:
        try:
            from dentists.models import DentistProfile
            initial["dentist"] = DentistProfile.objects.get(pk=dentist_id, is_available=True)
        except (DentistProfile.DoesNotExist, ValueError, TypeError):
            pass
    if service_id:
        try:
            from services.models import DentalService
            initial["service"] = DentalService.objects.get(pk=service_id, is_active=True)
        except (DentalService.DoesNotExist, ValueError, TypeError):
            pass

    booking_form = AppointmentBookingForm(initial=initial)

    if request.method == "POST":
        booking_form = AppointmentBookingForm(request.POST)
        if booking_form.is_valid():
            appt = booking_form.save(commit=False)
            appt.patient = profile
            appt.status = Appointment.Status.PENDING
            appt.save()
            notify_appointment_created(appt)
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
    raise PermissionDenied


@role_required(User.Role.PATIENT)
def patient_invoices_page(request):
    raise PermissionDenied


@role_required(User.Role.RECEPTIONIST)
def receptionist_appointments_page(request):
    from django.utils import timezone as tz
    from django.db.models import Q as _Q

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

    # Search / filter
    search = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "")
    date_filter = request.GET.get("date", "")

    all_appointments = None
    if search or status_filter or date_filter:
        qs = Appointment.objects.select_related("patient__user", "dentist__user").order_by("-appointment_date", "-appointment_time")
        if search:
            qs = qs.filter(
                _Q(patient__user__first_name__icontains=search)
                | _Q(patient__user__last_name__icontains=search)
                | _Q(dentist__user__last_name__icontains=search)
                | _Q(reason__icontains=search)
            )
        if status_filter:
            qs = qs.filter(status=status_filter)
        if date_filter:
            qs = qs.filter(appointment_date=date_filter)
        all_appointments = qs

    appointment_form = AppointmentManageForm(prefix="appointment")

    if request.method == "POST" and request.POST.get("form_type") == "appointment":
        appt_open = True
        appointment_form = AppointmentManageForm(request.POST, prefix="appointment")
        if appointment_form.is_valid():
            appointment = appointment_form.save()
            notify_appointment_created(appointment)
            messages.success(request, "Appointment created successfully.")
            return redirect("dashboard:receptionist_appointments")

    # KPIs for the appointments page
    from notifications.models import Notification
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    kpis = [
        {"label": "Today's Appointments", "value": today_schedule.count(), "icon": "event_available"},
        {"label": "Pending Requests", "value": pending_appointments.count(), "icon": "pending_actions"},
        {"label": "Confirmed", "value": Appointment.objects.filter(status=Appointment.Status.APPROVED).count(), "icon": "task_alt"},
        {"label": "Completed", "value": Appointment.objects.filter(status=Appointment.Status.COMPLETED).count(), "icon": "check_circle"},
    ]

    ctx = _receptionist_ctx(request.user)
    ctx.update({
        "today_schedule": today_schedule,
        "pending_appointments": pending_appointments,
        "all_appointments": all_appointments,
        "appointment_form": appointment_form,
        "appt_open": appt_open,
        "search": search,
        "status_filter": status_filter,
        "date_filter": date_filter,
        "kpis": kpis,
        "unread_count": unread_count,
    })
    return render(request, "dashboard/receptionist/appointments.html", ctx)


@role_required(User.Role.RECEPTIONIST)
def receptionist_notifications_page(request):
    from notifications.models import Notification

    type_filter = request.GET.get("type", "")
    unread_only = request.GET.get("unread", "") == "1"

    notifications_qs = Notification.objects.filter(user=request.user).order_by("-created_at")
    if type_filter:
        notifications_qs = notifications_qs.filter(notification_type=type_filter)
    if unread_only:
        notifications_qs = notifications_qs.filter(is_read=False)

    ctx = _receptionist_ctx(request.user)
    ctx.update({
        "notifications": notifications_qs,
        "type_filter": type_filter,
        "unread_only": unread_only,
    })
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
