from django import forms

from .models import Treatment


class TreatmentRecordForm(forms.ModelForm):
    class Meta:
        model = Treatment
        fields = ["patient", "dentist", "appointment", "diagnosis", "treatment_plan", "prescription", "treatment_date"]
        widgets = {
            "diagnosis": forms.Textarea(attrs={"rows": 3}),
            "treatment_plan": forms.Textarea(attrs={"rows": 4}),
            "prescription": forms.Textarea(attrs={"rows": 3}),
            "treatment_date": forms.DateInput(attrs={"type": "date"}),
        }


class DentistTreatmentForm(forms.ModelForm):
    """Treatment form for dentist dashboard: patient/dentist auto-resolved from appointment."""

    class Meta:
        model = Treatment
        fields = ["appointment", "diagnosis", "treatment_plan", "prescription", "treatment_date"]
        widgets = {
            "diagnosis": forms.Textarea(attrs={"rows": 3}),
            "treatment_plan": forms.Textarea(attrs={"rows": 4}),
            "prescription": forms.Textarea(attrs={"rows": 3}),
            "treatment_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, dentist=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._dentist = dentist
        from appointments.models import Appointment
        qs = Appointment.objects.none()
        if dentist:
            qs = (
                Appointment.objects.filter(
                    dentist=dentist,
                    status__in=[Appointment.Status.APPROVED, Appointment.Status.PENDING],
                )
                .select_related("patient__user")
            )
        self.fields["appointment"].queryset = qs

    def _post_clean(self):
        appt = self.cleaned_data.get("appointment") if hasattr(self, "cleaned_data") else None
        if appt:
            self.instance.patient = appt.patient
        if self._dentist:
            self.instance.dentist = self._dentist
        super()._post_clean()
