from django import forms

from .models import FollowUp


class FollowUpForm(forms.ModelForm):
    class Meta:
        model = FollowUp
        fields = ["patient", "appointment", "assigned_to", "followup_date", "reason", "notes", "status"]
        widgets = {
            "followup_date": forms.DateInput(attrs={"type": "date"}),
            "reason": forms.TextInput(),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from accounts.models import User
        self.fields["assigned_to"].queryset = User.objects.filter(
            role__in=["DENTIST", "RECEPTIONIST", "ADMIN"], is_active=True
        )
        self.fields["appointment"].required = False
        self.fields["assigned_to"].required = False
        self.fields["notes"].required = False
