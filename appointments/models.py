from django.db import models
from django.core.exceptions import ValidationError


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
                condition=models.Q(status__in=["pending", "approved", "completed"]),
                name="unique_dentist_appointment_slot",
            )
        ]

    def __str__(self):
        return f"{self.patient} with {self.dentist} on {self.appointment_date} at {self.appointment_time:%H:%M}"

    def clean(self):
        from .services import validate_appointment_slot

        validate_appointment_slot(self)
