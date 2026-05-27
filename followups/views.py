from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone as tz
from django.views.decorators.http import require_POST

from accounts.models import User
from accounts.permissions import role_required

from .forms import FollowUpForm
from .models import FollowUp


def _scope_followup_form(form, request):
    if request.user.role != User.Role.DENTIST:
        return form

    from appointments.models import Appointment
    from patients.models import PatientProfile

    form.fields["patient"].queryset = PatientProfile.objects.filter(
        appointments__dentist__user=request.user
    ).distinct()
    form.fields["appointment"].queryset = Appointment.objects.filter(
        dentist__user=request.user
    ).select_related("patient__user")
    form.fields["assigned_to"].queryset = User.objects.filter(pk=request.user.pk)
    form.fields["assigned_to"].initial = request.user
    return form


def _followup_ctx(request):
    from notifications.models import Notification
    from appointments.models import Appointment
    today = tz.localdate()
    return {
        "unread_count": Notification.objects.filter(user=request.user, is_read=False).count(),
        "today": today,
        "kpis": [
            {
                "label": "Today's Appointments",
                "value": Appointment.objects.filter(appointment_date=today).count(),
                "icon": "event_available",
            },
            {
                "label": "Pending Requests",
                "value": Appointment.objects.filter(status=Appointment.Status.PENDING).count(),
                "icon": "pending_actions",
            },
            {
                "label": "Follow-ups Today",
                "value": FollowUp.objects.filter(followup_date=today, status=FollowUp.Status.PENDING).count(),
                "icon": "next_plan",
            },
            {
                "label": "Overdue Follow-ups",
                "value": FollowUp.objects.filter(followup_date__lt=today, status=FollowUp.Status.PENDING).count(),
                "icon": "alarm",
            },
        ],
        "status_choices": Appointment.Status.choices,
    }


@role_required(User.Role.ADMIN, User.Role.DENTIST, User.Role.RECEPTIONIST)
def followup_list(request):
    today = tz.localdate()
    modal_open = False
    form = _scope_followup_form(FollowUpForm(), request)

    if request.method == "POST":
        modal_open = True
        form = _scope_followup_form(FollowUpForm(request.POST), request)
        if form.is_valid():
            followup = form.save(commit=False)
            if request.user.role == User.Role.DENTIST:
                followup.assigned_to = request.user
            followup.save()
            messages.success(request, "Follow-up created successfully.")
            return redirect("followups:list")

    qs = FollowUp.objects.select_related("patient__user", "appointment", "assigned_to")
    if request.user.role == User.Role.DENTIST:
        qs = qs.filter(assigned_to=request.user)

    # Filters
    status_filter = request.GET.get("status", "")
    date_filter = request.GET.get("date", "")
    search = request.GET.get("q", "").strip()

    if status_filter:
        qs = qs.filter(status=status_filter)
    if date_filter:
        qs = qs.filter(followup_date=date_filter)
    if search:
        qs = qs.filter(
            Q(patient__user__first_name__icontains=search)
            | Q(patient__user__last_name__icontains=search)
            | Q(reason__icontains=search)
        )

    # KPI counters (always unfiltered)
    all_fu = FollowUp.objects
    if request.user.role == User.Role.DENTIST:
        all_fu = all_fu.filter(assigned_to=request.user)
    kpis = [
        {"label": "Total Follow-ups", "value": all_fu.count(), "icon": "next_plan"},
        {"label": "Due Today", "value": all_fu.filter(followup_date=today, status=FollowUp.Status.PENDING).count(), "icon": "today"},
        {"label": "Overdue", "value": all_fu.filter(followup_date__lt=today, status=FollowUp.Status.PENDING).count(), "icon": "alarm"},
        {"label": "Completed", "value": all_fu.filter(status=FollowUp.Status.COMPLETED).count(), "icon": "check_circle"},
    ]

    from notifications.models import Notification
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()

    return render(request, "dashboard/receptionist/followups.html", {
        "followups": qs,
        "form": form,
        "modal_open": modal_open,
        "kpis": kpis,
        "status_filter": status_filter,
        "date_filter": date_filter,
        "search": search,
        "status_choices": FollowUp.Status.choices,
        "today": today,
        "unread_count": unread_count,
    })


@require_POST
@role_required(User.Role.ADMIN, User.Role.DENTIST, User.Role.RECEPTIONIST)
def followup_status(request, pk, status):
    qs = FollowUp.objects.all()
    if request.user.role == User.Role.DENTIST:
        qs = qs.filter(assigned_to=request.user)
    fu = get_object_or_404(qs, pk=pk)
    if status in FollowUp.Status.values:
        fu.status = status
        fu.save(update_fields=["status"])
        messages.success(request, f"Follow-up marked as {fu.get_status_display().lower()}.")
    return redirect("followups:list")


@require_POST
@role_required(User.Role.ADMIN, User.Role.DENTIST, User.Role.RECEPTIONIST)
def followup_delete(request, pk):
    qs = FollowUp.objects.all()
    if request.user.role == User.Role.DENTIST:
        qs = qs.filter(assigned_to=request.user)
    get_object_or_404(qs, pk=pk).delete()
    messages.success(request, "Follow-up deleted.")
    return redirect("followups:list")
