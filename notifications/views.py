from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import User
from accounts.permissions import get_dashboard_url_for_user
from .models import Notification, NotificationLog
from .services.twilio_service import send_sms, send_whatsapp


def _next_url(request):
    return (
        request.POST.get("next")
        or request.META.get("HTTP_REFERER")
        or get_dashboard_url_for_user(request.user)
    )


@require_POST
@login_required
def mark_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True})
    return redirect(_next_url(request))


@require_POST
@login_required
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True})
    return redirect(_next_url(request))


def _log_queryset_for_user(user):
    qs = NotificationLog.objects.select_related("patient__user", "appointment__dentist__user", "appointment__patient__user")
    if user.is_superuser or user.role == User.Role.ADMIN:
        return qs
    if user.role == User.Role.DENTIST:
        return qs.filter(Q(appointment__dentist__user=user) | Q(patient__appointments__dentist__user=user)).distinct()
    if user.role == User.Role.RECEPTIONIST:
        return qs.filter(appointment__isnull=False)
    return qs.none()


@login_required
def log_list(request):
    logs = _log_queryset_for_user(request.user)
    channel = request.GET.get("channel", "")
    status = request.GET.get("status", "")
    date = request.GET.get("date", "")
    patient = request.GET.get("patient", "").strip()

    if channel:
        logs = logs.filter(channel=channel)
    if status:
        logs = logs.filter(status=status)
    if date:
        logs = logs.filter(created_at__date=date)
    if patient:
        logs = logs.filter(
            Q(patient__user__first_name__icontains=patient)
            | Q(patient__user__last_name__icontains=patient)
            | Q(phone_number__icontains=patient)
        )

    if request.user.role == User.Role.RECEPTIONIST:
        base_template = "dashboard/receptionist_base.html"
    else:
        base_template = "dashboard/base.html"

    return render(
        request,
        "notifications/log_list.html",
        {
            "logs": logs[:200],
            "channel_choices": NotificationLog.Channel.choices,
            "status_choices": NotificationLog.Status.choices,
            "filters": {"channel": channel, "status": status, "date": date, "patient": patient},
            "base_template": base_template,
        },
    )


@require_POST
@login_required
def resend_log(request, pk):
    log = get_object_or_404(_log_queryset_for_user(request.user), pk=pk, status=NotificationLog.Status.FAILED)
    if log.channel == NotificationLog.Channel.SMS:
        result = send_sms(log.phone_number, log.message, patient=log.patient, appointment=log.appointment)
    else:
        result = send_whatsapp(log.phone_number, log.message, patient=log.patient, appointment=log.appointment)

    if result.get("ok"):
        messages.success(request, "Notification resent successfully.")
    else:
        messages.error(request, result.get("error", "Notification resend failed."))
    return redirect(request.META.get("HTTP_REFERER") or "notifications:logs")
