from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    patient = models.ForeignKey("patients.PatientProfile", on_delete=models.CASCADE, related_name="appointments")
    dentist = models.ForeignKey("dentists.DentistProfile", on_delete=models.PROTECT, related_name="appointments")
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["appointment_date", "appointment_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["dentist", "appointment_date", "appointment_time"],
                name="unique_dentist_appointment_slot",
            )
        ]

    def __str__(self):
        return f"{self.patient} with {self.dentist} on {self.appointment_date} at {self.appointment_time:%H:%M}"

    def clean(self):
        errors = {}
        today = timezone.localdate()

        if self.appointment_date and self.appointment_date < today:
            errors["appointment_date"] = "Appointment date cannot be in the past."
        if self.dentist_id and self.appointment_date:
            day_name = self.appointment_date.strftime("%A").lower()
            available_days = {day.strip().lower() for day in self.dentist.available_days.split(",") if day.strip()}
            if day_name not in available_days:
                errors["appointment_date"] = "Dentist is not available on this day."
        if self.dentist_id and self.appointment_time:
            if not (self.dentist.available_from <= self.appointment_time <= self.dentist.available_to):
                errors["appointment_time"] = "Appointment time is outside the dentist's available hours."
        if self.dentist_id and self.appointment_date and self.appointment_time:
            duplicate_slot = Appointment.objects.filter(
                dentist=self.dentist,
                appointment_date=self.appointment_date,
                appointment_time=self.appointment_time,
            ).exclude(pk=self.pk)
            if duplicate_slot.exists():
                errors["appointment_time"] = "This dentist already has an appointment at the selected date and time."

        if errors:
            raise ValidationError(errors)
