from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class DentistProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dentist_profile")
    specialization = models.CharField(max_length=120)
    license_number = models.CharField(max_length=80, unique=True)
    available_days = models.CharField(
        max_length=120,
        help_text="Comma-separated days, for example: Monday,Tuesday,Wednesday",
    )
    available_from = models.TimeField()
    available_to = models.TimeField()

    class Meta:
        ordering = ["user__last_name", "user__first_name"]

    def __str__(self):
        return f"Dr. {self.user.full_name or self.user.email} - {self.specialization}"

    def clean(self):
        errors = {}
        valid_days = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
        selected_days = {day.strip().lower() for day in self.available_days.split(",") if day.strip()}

        if self.user_id and self.user.role != self.user.Role.DENTIST:
            errors["user"] = "Dentist profiles can only be linked to users with the DENTIST role."
        if not selected_days:
            errors["available_days"] = "Enter at least one available day."
        elif invalid_days := selected_days - valid_days:
            errors["available_days"] = f"Invalid day(s): {', '.join(sorted(invalid_days))}."
        if self.available_from and self.available_to and self.available_from >= self.available_to:
            errors["available_to"] = "Available to must be later than available from."

        if errors:
            raise ValidationError(errors)
