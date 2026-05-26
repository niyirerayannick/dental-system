import re

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


def normalize_phone(raw):
    """Normalize Rwanda phone numbers to +2507XXXXXXXX format."""
    if not raw:
        return raw
    cleaned = re.sub(r'[\s\-\(\)]', '', str(raw))
    digits = cleaned.lstrip('+')
    if len(digits) == 10 and digits.startswith('07'):
        return '+250' + digits[1:]
    if len(digits) == 12 and digits.startswith('250'):
        return '+' + digits
    return cleaned if cleaned.startswith('+') else raw


class UserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("Users must have a phone number.")
        phone = normalize_phone(phone)
        email = extra_fields.pop("email", None)
        if email:
            email = self.normalize_email(email).lower()
        user = self.model(phone=phone, email=email or None, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("role", "ADMIN")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superusers must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superusers must have is_superuser=True.")

        return self.create_user(phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        DENTIST = "DENTIST", "Dentist"
        RECEPTIONIST = "RECEPTIONIST", "Receptionist"
        PATIENT = "PATIENT", "Patient"

    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True, blank=True, null=True)
    phone = models.CharField(max_length=20, unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PATIENT)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return self.full_name or self.phone

    def save(self, *args, **kwargs):
        if self.phone:
            self.phone = normalize_phone(self.phone)
        if self.email:
            self.email = self.__class__.objects.normalize_email(self.email.strip()).lower()
        if self.email == "":
            self.email = None
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def has_role(self, *roles):
        return self.role in roles
