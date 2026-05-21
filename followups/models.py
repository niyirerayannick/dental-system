from django.conf import settings
from django.db import models

from appointments.models import Appointment
from patients.models import PatientProfile


class FollowUp(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONTACTED = "contacted", "Contacted"
        COMPLETED = "completed", "Completed"
        MISSED = "missed", "Missed"

    patient = models.ForeignKey(
        PatientProfile,
        on_delete=models.CASCADE,
        related_name="followups",
    )
    appointment = models.ForeignKey(
        Appointment,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="followups",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_followups",
        limit_choices_to={"role__in": ["DENTIST", "RECEPTIONIST", "ADMIN"]},
    )
    followup_date = models.DateField()
    reason = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["followup_date", "status"]
        verbose_name = "Follow-up"
        verbose_name_plural = "Follow-ups"

    def __str__(self):
        return f"Follow-up: {self.patient} on {self.followup_date}"
