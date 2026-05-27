from django import forms
from django.core.exceptions import ValidationError

from accounts.models import User
from dentists.models import DentistProfile
from .models import Appointment


def available_dentists():
    return DentistProfile.objects.filter(
        user__role=User.Role.DENTIST,
        user__is_active=True,
        is_available=True,
    ).select_related("user")


class AppointmentBookingForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from services.models import DentalService
        self.fields["service"].queryset = DentalService.objects.filter(is_active=True).select_related("category")
        self.fields["service"].empty_label = "Select a service (optional)"
        self.fields["service"].required = False
        self.fields["dentist"].queryset = available_dentists()
        self.fields["reason"].required = True
        base_classes = "w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-900 shadow-sm outline-none transition focus:border-green-500 focus:ring-4 focus:ring-green-100"
        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = base_classes
            if field_name in {"reason", "notes"}:
                field.widget.attrs["placeholder"] = "Add a short description"
        self.fields["dentist"].empty_label = (
            "Choose a dentist" if self.fields["dentist"].queryset.exists() else "No dentists available yet"
        )
        self.fields["notes"].widget.attrs["placeholder"] = "Anything the dentist should know?"
        self.fields["dentist"].widget.attrs["data-availability-dentist"] = "true"
        self.fields["appointment_date"].widget.attrs["data-availability-date"] = "true"
        self.fields["appointment_time"].widget.attrs["data-availability-time"] = "true"
        self.fields["service"].widget.attrs["id"] = "id_service"

    class Meta:
        model = Appointment
        fields = ["service", "dentist", "appointment_date", "appointment_time", "reason", "notes"]
        widgets = {
            "appointment_date": forms.DateInput(attrs={"type": "date"}),
            "appointment_time": forms.TimeInput(attrs={"type": "time"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_status(self):
        return Appointment.Status.PENDING

    def clean(self):
        cleaned_data = super().clean()
        svc = cleaned_data.get("service")
        if svc:
            cleaned_data.setdefault("estimated_duration", svc.duration_minutes)
            if not cleaned_data.get("reason"):
                cleaned_data["reason"] = svc.name
        appointment = Appointment(
            dentist=cleaned_data.get("dentist"),
            appointment_date=cleaned_data.get("appointment_date"),
            appointment_time=cleaned_data.get("appointment_time"),
            reason=cleaned_data.get("reason", ""),
            notes=cleaned_data.get("notes", ""),
            status=Appointment.Status.PENDING,
        )
        try:
            appointment.clean()
        except ValidationError as error:
            if hasattr(error, "error_dict"):
                for field_name, field_errors in error.error_dict.items():
                    self.add_error(field_name if field_name in self.fields else None, field_errors)
            else:
                self.add_error(None, error)
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        svc = self.cleaned_data.get("service")
        if svc:
            instance.estimated_duration = svc.duration_minutes
        if commit:
            instance.save()
        return instance


class AppointmentManageForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patient"].queryset = self.fields["patient"].queryset.select_related("user")
        self.fields["dentist"].queryset = available_dentists()
        self.fields["dentist"].empty_label = (
            "Choose a dentist" if self.fields["dentist"].queryset.exists() else "No dentists available yet"
        )
        self.fields["dentist"].widget.attrs["data-availability-dentist"] = "true"
        self.fields["appointment_date"].widget.attrs["data-availability-date"] = "true"
        self.fields["appointment_time"].widget.attrs["data-availability-time"] = "true"

    class Meta:
        model = Appointment
        fields = ["patient", "dentist", "appointment_date", "appointment_time", "reason", "status", "notes"]
        widgets = {
            "appointment_date": forms.DateInput(attrs={"type": "date"}),
            "appointment_time": forms.TimeInput(attrs={"type": "time"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
