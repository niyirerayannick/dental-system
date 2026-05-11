from django import forms

from .models import Invoice


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["patient", "appointment", "amount", "status"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patient"].queryset = self.fields["patient"].queryset.select_related("user")
        self.fields["appointment"].queryset = self.fields["appointment"].queryset.select_related("patient__user", "dentist__user")
