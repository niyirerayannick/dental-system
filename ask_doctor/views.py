from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import User
from accounts.permissions import role_required

from .forms import AskDoctorForm, SendMessageForm
from .models import DoctorConversation, DoctorMessage


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _notif_count(user):
    try:
        from notifications.models import Notification
        return Notification.objects.filter(user=user, is_read=False).count()
    except Exception:
        return 0


def _patient_unread(user):
    """Unread staff replies for a patient."""
    return DoctorMessage.objects.filter(
        conversation__patient=user,
        is_read=False,
        sender__role__in=[User.Role.ADMIN, User.Role.DENTIST],
    ).count()


def _staff_total_unread(user):
    """Total unread patient messages visible to this staff member."""
    qs = DoctorMessage.objects.filter(
        is_read=False,
        sender__role=User.Role.PATIENT,
    )
    if user.role == User.Role.DENTIST:
        qs = qs.filter(
            Q(conversation__assigned_doctor=user)
            | Q(conversation__assigned_doctor__isnull=True)
        )
    return qs.count()


def _dentist_qs(user):
    """Base conversation queryset for a dentist: assigned + unassigned open/pending."""
    return DoctorConversation.objects.filter(
        Q(assigned_doctor=user)
        | Q(
            assigned_doctor__isnull=True,
            status__in=[DoctorConversation.Status.OPEN, DoctorConversation.Status.PENDING],
        )
    )


# ── Patient-side views ──────────────────────────────────────────────────────────

@login_required
def landing(request):
    """Public-facing landing page. Requires login; redirects staff to inbox."""
    role = request.user.role
    if role in (User.Role.ADMIN, User.Role.DENTIST):
        return redirect("ask_doctor:inbox")
    if role == User.Role.RECEPTIONIST:
        messages.error(request, "The Ask Doctor feature is for patients only.")
        return redirect("dashboard:receptionist")

    conversations = (
        DoctorConversation.objects
        .filter(patient=request.user)
        .prefetch_related("messages")
        .order_by("-updated_at")[:5]
    )
    return render(request, "ask_doctor/landing.html", {
        "conversations": conversations,
        "ask_unread": _patient_unread(request.user),
        "unread_count": _notif_count(request.user),
    })


@login_required
def conversation_list(request):
    if request.user.role != User.Role.PATIENT:
        return redirect("ask_doctor:inbox")

    qs = DoctorConversation.objects.filter(patient=request.user).order_by("-updated_at")
    status_filter = request.GET.get("status", "")
    if status_filter:
        qs = qs.filter(status=status_filter)

    paginator = Paginator(qs, 10)
    page = paginator.get_page(request.GET.get("page"))

    return render(request, "ask_doctor/conversation_list.html", {
        "conversations": page,
        "page_obj": page,
        "status_filter": status_filter,
        "status_choices": DoctorConversation.Status.choices,
        "ask_unread": _patient_unread(request.user),
        "unread_count": _notif_count(request.user),
    })


@login_required
def new_conversation(request):
    """Create a blank conversation, redirect to its detail."""
    if request.user.role != User.Role.PATIENT:
        raise PermissionDenied
    conv = DoctorConversation.objects.create(
        patient=request.user,
        status=DoctorConversation.Status.OPEN,
    )
    return redirect("ask_doctor:conversation_detail", pk=conv.pk)


@login_required
def conversation_detail(request, pk):
    if request.user.role != User.Role.PATIENT:
        # Staff hitting this URL go to inbox detail
        return redirect("ask_doctor:inbox_detail", pk=pk)

    conv = get_object_or_404(DoctorConversation, pk=pk, patient=request.user)

    # Mark all staff replies as read when patient views conversation
    conv.messages.filter(is_read=False).exclude(
        sender__role=User.Role.PATIENT
    ).update(is_read=True)

    if request.method == "POST":
        if conv.status == DoctorConversation.Status.CLOSED:
            messages.error(request, "This conversation is closed.")
            return redirect("ask_doctor:conversation_detail", pk=pk)

        form = SendMessageForm(request.POST, request.FILES)
        if form.is_valid():
            msg = DoctorMessage(
                conversation=conv,
                sender=request.user,
                message=form.cleaned_data["message"],
            )
            if form.cleaned_data.get("attachment"):
                msg.attachment = form.cleaned_data["attachment"]
            msg.save()
            conv.status = DoctorConversation.Status.PENDING
            conv.save()
            return redirect("ask_doctor:conversation_detail", pk=pk)
    else:
        form = SendMessageForm()

    chat_messages = conv.messages.select_related("sender").all()
    return render(request, "ask_doctor/conversation_detail.html", {
        "conversation": conv,
        "chat_messages": chat_messages,
        "form": form,
        "ask_unread": _patient_unread(request.user),
        "unread_count": _notif_count(request.user),
    })


@login_required
def ask_form(request):
    """Structured ask-a-doctor form for patients."""
    if request.user.role != User.Role.PATIENT:
        return redirect("ask_doctor:inbox")

    if request.method == "POST":
        form = AskDoctorForm(request.POST, request.FILES)
        if form.is_valid():
            category = form.cleaned_data.get("category", "")
            subject = form.cleaned_data["subject"]
            if category:
                label = dict(AskDoctorForm.CATEGORY_CHOICES).get(category, category)
                subject = f"[{label}] {subject}"

            conv = DoctorConversation.objects.create(
                patient=request.user,
                subject=subject,
                status=DoctorConversation.Status.OPEN,
            )
            DoctorMessage.objects.create(
                conversation=conv,
                sender=request.user,
                message=form.cleaned_data["message"],
                attachment=request.FILES.get("attachment"),
            )
            messages.success(
                request,
                "Your question has been submitted. Our team will respond within 24 hours.",
            )
            return redirect("ask_doctor:conversation_detail", pk=conv.pk)
    else:
        form = AskDoctorForm()

    return render(request, "ask_doctor/ask_form.html", {
        "form": form,
        "ask_unread": _patient_unread(request.user),
        "unread_count": _notif_count(request.user),
    })


@login_required
@require_POST
def close_conversation(request, pk):
    if request.user.role != User.Role.PATIENT:
        raise PermissionDenied
    conv = get_object_or_404(DoctorConversation, pk=pk, patient=request.user)
    conv.status = DoctorConversation.Status.CLOSED
    conv.save()
    messages.success(request, "Conversation closed.")
    return redirect("ask_doctor:conversation_list")


# ── Staff (dashboard) views ─────────────────────────────────────────────────────

@role_required(User.Role.ADMIN, User.Role.DENTIST)
def inbox(request):
    is_dentist = request.user.role == User.Role.DENTIST

    if is_dentist:
        qs = _dentist_qs(request.user)
    else:
        qs = DoctorConversation.objects.all()

    qs = qs.select_related("patient", "assigned_doctor").prefetch_related("messages")

    status_filter = request.GET.get("status", "open")
    if status_filter and status_filter != "all":
        qs = qs.filter(status=status_filter)

    qs = qs.order_by("-updated_at")
    total_unread = _staff_total_unread(request.user)

    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get("page"))

    # Count per status for badge display
    base = DoctorConversation.objects.all() if not is_dentist else _dentist_qs(request.user)
    status_counts = {
        "open": base.filter(status="open").count(),
        "pending": base.filter(status="pending").count(),
        "answered": base.filter(status="answered").count(),
        "closed": base.filter(status="closed").count(),
    }

    return render(request, "ask_doctor/inbox.html", {
        "conversations": page,
        "page_obj": page,
        "status_filter": status_filter,
        "status_choices": DoctorConversation.Status.choices,
        "total_unread": total_unread,
        "status_counts": status_counts,
        "is_dentist": is_dentist,
    })


@role_required(User.Role.ADMIN, User.Role.DENTIST)
def inbox_detail(request, pk):
    is_dentist = request.user.role == User.Role.DENTIST

    if is_dentist:
        conv = get_object_or_404(
            _dentist_qs(request.user),
            pk=pk,
        )
    else:
        conv = get_object_or_404(DoctorConversation, pk=pk)

    # Mark patient messages as read when staff opens conversation
    conv.messages.filter(is_read=False, sender__role=User.Role.PATIENT).update(is_read=True)

    # Build assign form choices
    staff_users = User.objects.filter(
        role__in=[User.Role.ADMIN, User.Role.DENTIST],
        is_active=True,
    ).order_by("last_name", "first_name")

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "reply":
            form = SendMessageForm(request.POST, request.FILES)
            if form.is_valid():
                msg = DoctorMessage(
                    conversation=conv,
                    sender=request.user,
                    message=form.cleaned_data["message"],
                )
                if form.cleaned_data.get("attachment"):
                    msg.attachment = form.cleaned_data["attachment"]
                msg.save()
                conv.status = DoctorConversation.Status.ANSWERED
                conv.save()
                messages.success(request, "Reply sent to patient.")
                return redirect("ask_doctor:inbox_detail", pk=pk)

        elif action == "assign":
            doctor_id = request.POST.get("assigned_doctor", "")
            if doctor_id:
                doctor = get_object_or_404(User, pk=doctor_id, is_active=True)
                conv.assigned_doctor = doctor
            else:
                conv.assigned_doctor = None
            conv.save()
            messages.success(request, "Assigned doctor updated.")
            return redirect("ask_doctor:inbox_detail", pk=pk)

        elif action == "close":
            conv.status = DoctorConversation.Status.CLOSED
            conv.save()
            messages.success(request, "Conversation closed.")
            return redirect("ask_doctor:inbox")

        elif action == "reopen":
            conv.status = DoctorConversation.Status.OPEN
            conv.save()
            messages.success(request, "Conversation reopened.")
            return redirect("ask_doctor:inbox_detail", pk=pk)

    form = SendMessageForm()
    chat_messages = conv.messages.select_related("sender").all()

    return render(request, "ask_doctor/inbox_detail.html", {
        "conversation": conv,
        "chat_messages": chat_messages,
        "form": form,
        "staff_users": staff_users,
        "is_dentist": is_dentist,
        "total_unread": _staff_total_unread(request.user),
    })
