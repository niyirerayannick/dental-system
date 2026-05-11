from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class Treatment(models.Model):
    patient = models.ForeignKey("patients.PatientProfile", on_delete=models.CASCADE, related_name="treatments")
    dentist = models.ForeignKey("dentists.DentistProfile", on_delete=models.PROTECT, related_name="treatments")
    appointment = models.OneToOneField(
        "appointments.Appointment",
        on_delete=models.SET_NULL,
        related_name="treatment",
        null=True,
        blank=True,
    )
    diagnosis = models.TextField()
    treatment_plan = models.TextField()
    prescription = models.TextField(blank=True)
    treatment_date = models.DateField(default=timezone.localdate)

    class Meta:
        ordering = ["-treatment_date"]

    def __str__(self):
        return f"Treatment for {self.patient} on {self.treatment_date}"

    def clean(self):
        errors = {}
        if self.treatment_date and self.treatment_date > timezone.localdate():
            errors["treatment_date"] = "Treatment date cannot be in the future."
        if self.appointment_id:
            if self.appointment.patient_id != self.patient_id:
                errors["patient"] = "Patient must match the selected appointment."
            if self.appointment.dentist_id != self.dentist_id:
                errors["dentist"] = "Dentist must match the selected appointment."

        if errors:
            raise ValidationError(errors)
