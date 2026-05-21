from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.crypto import get_random_string

from accounts.models import User
from .models import DentistDaySchedule, DentistProfile, WEEKDAYS

_TIME_INPUT = {"type": "time"}
_FIELD_CLS = (
    "w-full rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-sm "
    "focus:border-green-400 focus:outline-none focus:ring-2 focus:ring-green-100"
)


def _time_field(**kwargs):
    return forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={"type": "time", "class": _FIELD_CLS}),
        **kwargs,
    )


class DentistForm(forms.Form):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone = forms.CharField(max_length=30, required=False)
    specialization = forms.CharField(max_length=120)
    license_number = forms.CharField(max_length=80)
    appointment_duration = forms.IntegerField(min_value=5, initial=30, help_text="Minutes per appointment.")
    max_patients_per_day = forms.IntegerField(min_value=1, initial=12)
    is_available = forms.BooleanField(required=False, initial=True)
    is_active = forms.BooleanField(required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("first_name", "last_name", "email", "phone",
                     "specialization", "license_number",
                     "appointment_duration", "max_patients_per_day"):
            self.fields[name].widget.attrs["class"] = _FIELD_CLS
        for day in WEEKDAYS:
            self.fields[f"{day}_working"] = forms.BooleanField(required=False, label=day.capitalize())
            self.fields[f"{day}_start"] = _time_field(label="Start")
            self.fields[f"{day}_end"] = _time_field(label="End")
            self.fields[f"{day}_break_start"] = _time_field(label="Break start")
            self.fields[f"{day}_break_end"] = _time_field(label="Break end")

    def clean(self):
        cleaned = super().clean()
        any_working = False
        for day in WEEKDAYS:
            if not cleaned.get(f"{day}_working"):
                continue
            any_working = True
            start = cleaned.get(f"{day}_start")
            end = cleaned.get(f"{day}_end")
            bstart = cleaned.get(f"{day}_break_start")
            bend = cleaned.get(f"{day}_break_end")
            if not start:
                self.add_error(f"{day}_start", "Start time required.")
            if not end:
                self.add_error(f"{day}_end", "End time required.")
            if start and end:
                if start >= end:
                    self.add_error(f"{day}_end", "End must be after start.")
                if bstart and bend:
                    if bstart >= bend:
                        self.add_error(f"{day}_break_end", "Break end must be after break start.")
                    elif not (start <= bstart < bend <= end):
                        self.add_error(f"{day}_break_start", "Break must be within working hours.")
        if not any_working:
            raise forms.ValidationError("Select at least one working day.")
        return cleaned

    def clean_email(self):
        email = get_user_model().objects.normalize_email(self.cleaned_data["email"]).lower()
        if get_user_model().objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean_license_number(self):
        ln = self.cleaned_data["license_number"]
        if DentistProfile.objects.filter(license_number=ln).exists():
            raise forms.ValidationError("A dentist with this license number already exists.")
        return ln

    def _save_day_schedules(self, profile):
        profile.day_schedules.all().delete()
        for day in WEEKDAYS:
            if self.cleaned_data.get(f"{day}_working"):
                DentistDaySchedule.objects.create(
                    dentist=profile,
                    day=day,
                    start_time=self.cleaned_data[f"{day}_start"],
                    end_time=self.cleaned_data[f"{day}_end"],
                    break_start=self.cleaned_data.get(f"{day}_break_start") or None,
                    break_end=self.cleaned_data.get(f"{day}_break_end") or None,
                )

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
        profile.specialization = self.cleaned_data["specialization"]
        profile.license_number = self.cleaned_data["license_number"]
        profile.appointment_duration = self.cleaned_data["appointment_duration"]
        profile.max_patients_per_day = self.cleaned_data["max_patients_per_day"]
        profile.is_available = self.cleaned_data.get("is_available", True)
        profile.save(update_fields=[
            "specialization", "license_number",
            "appointment_duration", "max_patients_per_day", "is_available",
        ])
        self._save_day_schedules(profile)
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
                "appointment_duration": instance.appointment_duration,
                "max_patients_per_day": instance.max_patients_per_day,
                "is_available": instance.is_available,
                "is_active": instance.user.is_active,
            })
            for sched in instance.day_schedules.all():
                d = sched.day
                initial[f"{d}_working"] = True
                initial[f"{d}_start"] = sched.start_time
                initial[f"{d}_end"] = sched.end_time
                initial[f"{d}_break_start"] = sched.break_start
                initial[f"{d}_break_end"] = sched.break_end
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
        ln = self.cleaned_data["license_number"]
        qs = DentistProfile.objects.filter(license_number=ln)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A dentist with this license number already exists.")
        return ln

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

        profile.specialization = self.cleaned_data["specialization"]
        profile.license_number = self.cleaned_data["license_number"]
        profile.appointment_duration = self.cleaned_data["appointment_duration"]
        profile.max_patients_per_day = self.cleaned_data["max_patients_per_day"]
        profile.is_available = self.cleaned_data.get("is_available", True)
        profile.save(update_fields=[
            "specialization", "license_number",
            "appointment_duration", "max_patients_per_day", "is_available",
        ])
        self._save_day_schedules(profile)
        return profile
