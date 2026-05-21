from django import forms
from .models import DentalService, ServiceCategory

_FIELD_CLASSES = (
    "w-full rounded-2xl border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm "
    "focus:border-green-400 focus:outline-none focus:ring-2 focus:ring-green-100"
)


class ServiceCategoryForm(forms.ModelForm):
    class Meta:
        model = ServiceCategory
        fields = ["name", "icon", "description", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = _FIELD_CLASSES


class DentalServiceForm(forms.ModelForm):
    class Meta:
        model = DentalService
        fields = ["category", "name", "description", "duration_minutes", "base_price", "icon", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = ServiceCategory.objects.filter(is_active=True)
        self.fields["category"].empty_label = "Select category"
        for field in self.fields.values():
            field.widget.attrs["class"] = _FIELD_CLASSES
