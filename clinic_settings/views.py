from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import redirect, render

from accounts.models import User
from accounts.permissions import role_required

from .forms import (
    AccountSettingsForm,
    AppointmentSettingsForm,
    BillingSettingsForm,
    ClinicProfileForm,
    NotificationSettingsForm,
    SecuritySettingsForm,
)
from .models import ClinicSetting


@role_required(User.Role.ADMIN)
def settings_view(request):
    clinic = ClinicSetting.get_settings()
    active_tab = request.GET.get("tab", "clinic")

    forms = {
        "clinic": ClinicProfileForm(instance=clinic, prefix="clinic"),
        "appointment": AppointmentSettingsForm(instance=clinic, prefix="appointment"),
        "notification": NotificationSettingsForm(instance=clinic, prefix="notification"),
        "billing": BillingSettingsForm(instance=clinic, prefix="billing"),
        "security": SecuritySettingsForm(instance=clinic, prefix="security"),
        "account": AccountSettingsForm(instance=request.user, prefix="account"),
        "password": PasswordChangeForm(request.user, prefix="password"),
    }

    if request.method == "POST":
        section = request.POST.get("section", "")
        active_tab = section if section in ("clinic", "appointment", "notification", "billing", "security", "account", "password") else active_tab

        if section == "clinic":
            f = ClinicProfileForm(request.POST, request.FILES, instance=clinic, prefix="clinic")
            forms["clinic"] = f
            if f.is_valid():
                f.save()
                messages.success(request, "Clinic profile updated successfully.")
                return redirect(f"{request.path}?tab=clinic")

        elif section == "appointment":
            f = AppointmentSettingsForm(request.POST, instance=clinic, prefix="appointment")
            forms["appointment"] = f
            if f.is_valid():
                f.save()
                messages.success(request, "Appointment settings updated successfully.")
                return redirect(f"{request.path}?tab=appointment")

        elif section == "notification":
            f = NotificationSettingsForm(request.POST, instance=clinic, prefix="notification")
            forms["notification"] = f
            if f.is_valid():
                f.save()
                messages.success(request, "Notification settings updated successfully.")
                return redirect(f"{request.path}?tab=notification")

        elif section == "billing_settings":
            f = BillingSettingsForm(request.POST, instance=clinic, prefix="billing")
            forms["billing"] = f
            if f.is_valid():
                f.save()
                messages.success(request, "Billing settings updated successfully.")
                return redirect(f"{request.path}?tab=billing")

        elif section == "security":
            f = SecuritySettingsForm(request.POST, instance=clinic, prefix="security")
            forms["security"] = f
            if f.is_valid():
                f.save()
                messages.success(request, "Security settings updated successfully.")
                return redirect(f"{request.path}?tab=security")

        elif section == "account":
            f = AccountSettingsForm(request.POST, instance=request.user, prefix="account")
            forms["account"] = f
            if f.is_valid():
                f.save()
                messages.success(request, "Account settings updated successfully.")
                return redirect(f"{request.path}?tab=account")

        elif section == "password":
            f = PasswordChangeForm(request.user, request.POST, prefix="password")
            forms["password"] = f
            if f.is_valid():
                user = f.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed successfully.")
                return redirect(f"{request.path}?tab=account")

        # If the posted section maps to billing tab, keep active_tab = billing
        if section == "billing_settings":
            active_tab = "billing"

    return render(
        request,
        "clinic_settings/settings.html",
        {"forms": forms, "active_tab": active_tab, "clinic": clinic},
    )
