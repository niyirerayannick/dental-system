from django.db import models


class ClinicSetting(models.Model):
    # Clinic Profile
    clinic_name = models.CharField(max_length=200, default="DentalCare Clinic")
    clinic_email = models.EmailField(blank=True)
    clinic_phone = models.CharField(max_length=30, blank=True)
    clinic_address = models.TextField(blank=True)
    website = models.URLField(blank=True)
    logo = models.FileField(upload_to="clinic/logo/", blank=True, null=True)

    # Appointment Settings
    opening_time = models.TimeField(default="08:00")
    closing_time = models.TimeField(default="17:00")
    appointment_duration = models.PositiveIntegerField(default=30)
    allow_online_booking = models.BooleanField(default=True)
    auto_approve_appointments = models.BooleanField(default=False)

    # Notification Settings
    enable_email_notifications = models.BooleanField(default=True)
    enable_sms_notifications = models.BooleanField(default=False)
    appointment_reminder_time = models.PositiveIntegerField(default=24)
    admin_email = models.EmailField(blank=True)

    # Billing Settings
    currency = models.CharField(max_length=10, default="USD")
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    invoice_prefix = models.CharField(max_length=20, default="INV")
    payment_methods = models.CharField(max_length=200, blank=True, default="Cash,Card")

    # Security Settings
    require_strong_password = models.BooleanField(default=True)
    session_timeout = models.PositiveIntegerField(default=30)
    enable_two_factor_auth = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Clinic Setting"

    def __str__(self):
        return self.clinic_name

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
