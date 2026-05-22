from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


DEFAULT_AVAILABLE_DAYS = "Monday,Tuesday,Wednesday,Thursday,Friday"
DEFAULT_AVAILABLE_FROM = "09:00"
DEFAULT_AVAILABLE_TO = "17:00"
DEFAULT_APPOINTMENT_DURATION = 30
DEFAULT_MAX_PATIENTS_PER_DAY = 12


class DentistProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dentist_profile")
    specialization = models.CharField(max_length=120, blank=True)
    license_number = models.CharField(max_length=80, unique=True, blank=True)
    available_days = models.CharField(
        max_length=120,
        default=DEFAULT_AVAILABLE_DAYS,
        help_text="Comma-separated days, for example: Monday,Tuesday,Wednesday",
    )
    available_from = models.TimeField(default=DEFAULT_AVAILABLE_FROM)
    available_to = models.TimeField(default=DEFAULT_AVAILABLE_TO)
    appointment_duration = models.PositiveIntegerField(default=DEFAULT_APPOINTMENT_DURATION)
    max_patients_per_day = models.PositiveIntegerField(default=DEFAULT_MAX_PATIENTS_PER_DAY)
    break_start_time = models.TimeField(null=True, blank=True)
    break_end_time = models.TimeField(null=True, blank=True)
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ["user__last_name", "user__first_name"]

    def __str__(self):
        name = self.user.full_name or self.user.phone
        if self.specialization:
            return f"Dr. {name} - {self.specialization}"
        return f"Dr. {name}"

    @classmethod
    def default_license_number(cls, user):
        base = user.pk or timezone.now().strftime("%Y%m%d%H%M%S")
        return f"AUTO-DENTIST-{base}"

    @classmethod
    def ensure_for_user(cls, user):
        if user.role != user.Role.DENTIST:
            return None
        profile, created = cls.objects.get_or_create(
            user=user,
            defaults={
                "license_number": cls.default_license_number(user),
                "available_days": DEFAULT_AVAILABLE_DAYS,
                "available_from": DEFAULT_AVAILABLE_FROM,
                "available_to": DEFAULT_AVAILABLE_TO,
                "appointment_duration": DEFAULT_APPOINTMENT_DURATION,
                "max_patients_per_day": DEFAULT_MAX_PATIENTS_PER_DAY,
            },
        )
        if not profile.license_number:
            profile.license_number = cls.default_license_number(user)
            profile.save(update_fields=["license_number"])
        return profile

    def clean(self):
        errors = {}
        valid_days = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
        selected_days = {day.strip().lower() for day in self.available_days.split(",") if day.strip()}

        if self.user_id and self.user.role != self.user.Role.DENTIST:
            errors["user"] = "Dentist profiles can only be linked to users with the DENTIST role."
        if self.appointment_duration <= 0:
            errors["appointment_duration"] = "Appointment duration must be greater than zero."
        if self.max_patients_per_day <= 0:
            errors["max_patients_per_day"] = "Max patients per day must be greater than zero."
        if not selected_days:
            errors["available_days"] = "Enter at least one available day."
        elif invalid_days := selected_days - valid_days:
            errors["available_days"] = f"Invalid day(s): {', '.join(sorted(invalid_days))}."
        if self.available_from and self.available_to and self.available_from >= self.available_to:
            errors["available_to"] = "Available to must be later than available from."
        if self.break_start_time and self.break_end_time:
            if self.break_start_time >= self.break_end_time:
                errors["break_end_time"] = "Break end time must be later than break start time."
            elif self.available_from and self.available_to and not (
                self.available_from <= self.break_start_time < self.break_end_time <= self.available_to
            ):
                errors["break_start_time"] = "Break time must be inside working hours."

        if errors:
            raise ValidationError(errors)


WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
WEEKDAY_ORDER = {d: i for i, d in enumerate(WEEKDAYS)}


class DentistDaySchedule(models.Model):
    DAY_CHOICES = [(d, d.capitalize()) for d in WEEKDAYS]

    dentist = models.ForeignKey(DentistProfile, on_delete=models.CASCADE, related_name="day_schedules")
    day = models.CharField(max_length=10, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    break_start = models.TimeField(null=True, blank=True)
    break_end = models.TimeField(null=True, blank=True)

    class Meta:
        unique_together = [("dentist", "day")]

    def __str__(self):
        return f"{self.get_day_display()} {self.start_time:%H:%M}–{self.end_time:%H:%M}"

    def clean(self):
        errors = {}
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            errors["end_time"] = "End time must be after start time."
        if self.break_start and self.break_end:
            if self.break_start >= self.break_end:
                errors["break_end"] = "Break end must be after break start."
            elif self.start_time and self.end_time and not (
                self.start_time <= self.break_start < self.break_end <= self.end_time
            ):
                errors["break_start"] = "Break must be within working hours."
        if errors:
            raise ValidationError(errors)
