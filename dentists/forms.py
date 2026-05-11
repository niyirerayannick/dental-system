from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.crypto import get_random_string

from accounts.models import User
from .models import DentistProfile


class DentistForm(forms.Form):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone = forms.CharField(max_length=30, required=False)
    specialization = forms.CharField(max_length=120)
    license_number = forms.CharField(max_length=80)
    available_days = forms.CharField(max_length=120, help_text="Example: Monday,Tuesday,Wednesday")
    available_from = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))
    available_to = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))
    is_active = forms.BooleanField(required=False, initial=True)

    def clean_email(self):
        email = get_user_model().objects.normalize_email(self.cleaned_data["email"]).lower()
        if get_user_model().objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean_license_number(self):
        license_number = self.cleaned_data["license_number"]
        if DentistProfile.objects.filter(license_number=license_number).exists():
            raise forms.ValidationError("A dentist with this license number already exists.")
        return license_number

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("available_from") and cleaned_data.get("available_to"):
            if cleaned_data["available_from"] >= cleaned_data["available_to"]:
                self.add_error("available_to", "Available to must be later than available from.")
        return cleaned_data

    @transaction.atomic
    def save(self):
        user = User.objects.create_user(
            email=self.cleaned_data["email"],
            password=get_random_string(32),
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
            phone=self.cleaned_data["phone"],
            role=User.Role.DENTIST,
            is_active=self.cleaned_data.get("is_active", False),
        )
        return DentistProfile.objects.create(
            user=user,
            specialization=self.cleaned_data["specialization"],
            license_number=self.cleaned_data["license_number"],
            available_days=self.cleaned_data["available_days"],
            available_from=self.cleaned_data["available_from"],
            available_to=self.cleaned_data["available_to"],
        )
