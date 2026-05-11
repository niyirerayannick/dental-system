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
