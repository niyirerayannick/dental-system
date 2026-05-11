from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Invoice(models.Model):
    class Status(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    patient = models.ForeignKey("patients.PatientProfile", on_delete=models.CASCADE, related_name="invoices")
    appointment = models.ForeignKey(
        "appointments.Appointment",
        on_delete=models.SET_NULL,
        related_name="invoices",
        null=True,
        blank=True,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UNPAID)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invoice #{self.pk or 'new'} - {self.patient} - {self.amount}"

    def clean(self):
        if self.appointment_id and self.appointment.patient_id != self.patient_id:
            from django.core.exceptions import ValidationError

            raise ValidationError({"appointment": "Appointment must belong to the selected patient."})
