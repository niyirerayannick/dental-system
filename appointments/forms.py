from django import forms
from django.core.exceptions import ValidationError

from .models import Appointment


class AppointmentBookingForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["dentist"].queryset = self.fields["dentist"].queryset.select_related("user")
        self.fields["reason"].required = True

    class Meta:
        model = Appointment
        fields = ["dentist", "appointment_date", "appointment_time", "reason", "notes"]
        widgets = {
            "appointment_date": forms.DateInput(attrs={"type": "date"}),
            "appointment_time": forms.TimeInput(attrs={"type": "time"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_status(self):
        return Appointment.Status.PENDING

    def clean(self):
        cleaned_data = super().clean()
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


class AppointmentManageForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patient"].queryset = self.fields["patient"].queryset.select_related("user")
        self.fields["dentist"].queryset = self.fields["dentist"].queryset.select_related("user")

    class Meta:
        model = Appointment
        fields = ["patient", "dentist", "appointment_date", "appointment_time", "reason", "status", "notes"]
        widgets = {
            "appointment_date": forms.DateInput(attrs={"type": "date"}),
            "appointment_time": forms.TimeInput(attrs={"type": "time"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
