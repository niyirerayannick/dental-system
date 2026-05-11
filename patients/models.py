from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class PatientProfile(models.Model):
    class Gender(models.TextChoices):
        FEMALE = "female", "Female"
        MALE = "male", "Male"
        OTHER = "other", "Other"
        PREFER_NOT_TO_SAY = "prefer_not_to_say", "Prefer not to say"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="patient_profile")
    profile_image = models.ImageField(upload_to="profile_images/", null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=Gender.choices, blank=True)
    address = models.TextField(blank=True)
    emergency_contact = models.CharField(max_length=150, blank=True)
    medical_history = models.TextField(blank=True)
    allergies = models.TextField(blank=True)

    class Meta:
        ordering = ["user__last_name", "user__first_name"]

    def __str__(self):
        return self.user.full_name or self.user.email

    def clean(self):
        if self.user_id and self.user.role != self.user.Role.PATIENT:
            raise ValidationError({"user": "Patient profiles can only be linked to users with the PATIENT role."})
