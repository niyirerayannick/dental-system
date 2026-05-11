from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.crypto import get_random_string

from accounts.models import User
from .models import DentistProfile


DAY_CHOICES = [
    ("Monday", "Monday"),
    ("Tuesday", "Tuesday"),
    ("Wednesday", "Wednesday"),
    ("Thursday", "Thursday"),
    ("Friday", "Friday"),
    ("Saturday", "Saturday"),
    ("Sunday", "Sunday"),
]


class DentistForm(forms.Form):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone = forms.CharField(max_length=30, required=False)
    specialization = forms.CharField(max_length=120)
    license_number = forms.CharField(max_length=80)
    available_days = forms.MultipleChoiceField(
        choices=DAY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        help_text="Choose the days this dentist accepts appointments.",
    )
    available_from = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))
    available_to = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))
    appointment_duration = forms.IntegerField(min_value=5, initial=30, help_text="Minutes per appointment.")
    max_patients_per_day = forms.IntegerField(min_value=1, initial=12)
    break_start_time = forms.TimeField(required=False, widget=forms.TimeInput(attrs={"type": "time"}))
    break_end_time = forms.TimeField(required=False, widget=forms.TimeInput(attrs={"type": "time"}))
    is_available = forms.BooleanField(required=False, initial=True)
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
        if cleaned_data.get("break_start_time") and cleaned_data.get("break_end_time"):
            if cleaned_data["break_start_time"] >= cleaned_data["break_end_time"]:
                self.add_error("break_end_time", "Break end time must be later than break start time.")
            elif cleaned_data.get("available_from") and cleaned_data.get("available_to") and not (
                cleaned_data["available_from"] <= cleaned_data["break_start_time"] < cleaned_data["break_end_time"] <= cleaned_data["available_to"]
            ):
                self.add_error("break_start_time", "Break time must be inside working hours.")
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
        profile = DentistProfile.ensure_for_user(user)
        for field in [
            "specialization",
            "license_number",
            "available_from",
            "available_to",
            "appointment_duration",
            "max_patients_per_day",
            "break_start_time",
            "break_end_time",
            "is_available",
        ]:
            setattr(profile, field, self.cleaned_data[field])
        profile.available_days = ",".join(self.cleaned_data["available_days"])
        profile.save(
            update_fields=[
                "specialization",
                "license_number",
                "available_days",
                "available_from",
                "available_to",
                "appointment_duration",
                "max_patients_per_day",
                "break_start_time",
                "break_end_time",
                "is_available",
            ]
        )
        return profile


class DentistEditForm(DentistForm):
    def __init__(self, *args, instance=None, **kwargs):
        self.instance = instance
        initial = kwargs.pop("initial", {})
        if instance:
            initial.update({
                "first_name": instance.user.first_name,
                "last_name": instance.user.last_name,
                "email": instance.user.email,
                "phone": instance.user.phone,
                "specialization": instance.specialization,
                "license_number": instance.license_number,
                "available_days": [day.strip() for day in instance.available_days.split(",") if day.strip()],
                "available_from": instance.available_from,
                "available_to": instance.available_to,
                "appointment_duration": instance.appointment_duration,
                "max_patients_per_day": instance.max_patients_per_day,
                "break_start_time": instance.break_start_time,
                "break_end_time": instance.break_end_time,
                "is_available": instance.is_available,
                "is_active": instance.user.is_active,
            })
        super().__init__(*args, initial=initial, **kwargs)

    def clean_email(self):
        email = get_user_model().objects.normalize_email(self.cleaned_data["email"]).lower()
        qs = get_user_model().objects.filter(email=email)
        if self.instance:
            qs = qs.exclude(pk=self.instance.user_id)
        if qs.exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean_license_number(self):
        license_number = self.cleaned_data["license_number"]
        qs = DentistProfile.objects.filter(license_number=license_number)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A dentist with this license number already exists.")
        return license_number

    @transaction.atomic
    def save(self):
        profile = self.instance
        user = profile.user
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        user.phone = self.cleaned_data["phone"]
        user.role = User.Role.DENTIST
        user.is_active = self.cleaned_data.get("is_active", False)
        user.save(update_fields=["first_name", "last_name", "email", "phone", "role", "is_active"])

        for field in [
            "specialization",
            "license_number",
            "available_from",
            "available_to",
            "appointment_duration",
            "max_patients_per_day",
            "break_start_time",
            "break_end_time",
            "is_available",
        ]:
            setattr(profile, field, self.cleaned_data[field])
        profile.available_days = ",".join(self.cleaned_data["available_days"])
        profile.save(
            update_fields=[
                "specialization",
                "license_number",
                "available_days",
                "available_from",
                "available_to",
                "appointment_duration",
                "max_patients_per_day",
                "break_start_time",
                "break_end_time",
                "is_available",
            ]
        )
        return profile
