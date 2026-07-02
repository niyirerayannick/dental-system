from django import forms
from django.contrib.auth import get_user_model

from dental_system.upload_validation import validate_uploaded_image
from .models import ClinicSetting

User = get_user_model()


class ClinicProfileForm(forms.ModelForm):
    class Meta:
        model = ClinicSetting
        fields = ["clinic_name", "clinic_email", "clinic_phone", "clinic_address", "website", "logo"]
        widgets = {
            "clinic_address": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_logo(self):
        logo = self.cleaned_data.get("logo")
        validate_uploaded_image(logo)
        return logo


class AppointmentSettingsForm(forms.ModelForm):
    class Meta:
        model = ClinicSetting
        fields = [
            "opening_time",
            "closing_time",
            "appointment_duration",
            "allow_online_booking",
            "auto_approve_appointments",
        ]


class NotificationSettingsForm(forms.ModelForm):
    class Meta:
        model = ClinicSetting
        fields = [
            "enable_email_notifications",
            "enable_sms_notifications",
            "appointment_reminder_time",
            "admin_email",
        ]


class BillingSettingsForm(forms.ModelForm):
    class Meta:
        model = ClinicSetting
        fields = ["currency", "tax_percentage", "invoice_prefix", "payment_methods"]


class SecuritySettingsForm(forms.ModelForm):
    class Meta:
        model = ClinicSetting
        fields = ["require_strong_password", "session_timeout", "enable_two_factor_auth"]


class AccountSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone"]
