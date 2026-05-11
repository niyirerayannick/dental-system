from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import get_random_string

from accounts.models import User
from .models import PatientProfile


class PatientProfileForm(forms.ModelForm):
    class Meta:
        model = PatientProfile
        fields = ["date_of_birth", "gender", "address", "emergency_contact", "medical_history", "allergies"]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "address": forms.Textarea(attrs={"rows": 3}),
            "medical_history": forms.Textarea(attrs={"rows": 4}),
            "allergies": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get("date_of_birth")
        if date_of_birth and date_of_birth > timezone.localdate():
            raise forms.ValidationError("Date of birth cannot be in the future.")
        return date_of_birth


class PatientRegistrationForm(forms.Form):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone = forms.CharField(max_length=30, required=False)
    date_of_birth = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    gender = forms.ChoiceField(required=False, choices=[("", "---------")] + list(PatientProfile.Gender.choices))
    address = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    emergency_contact = forms.CharField(max_length=150, required=False)
    medical_history = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}))
    allergies = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def clean_email(self):
        email = get_user_model().objects.normalize_email(self.cleaned_data["email"]).lower()
        if get_user_model().objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        allowed = set("+()-. 0123456789")
        if phone and any(character not in allowed for character in phone):
            raise forms.ValidationError("Enter a valid phone number.")
        return phone

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get("date_of_birth")
        if date_of_birth and date_of_birth > timezone.localdate():
            raise forms.ValidationError("Date of birth cannot be in the future.")
        return date_of_birth

    @transaction.atomic
    def save(self):
        user = User.objects.create_user(
            email=self.cleaned_data["email"],
            password=get_random_string(32),
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
            phone=self.cleaned_data["phone"],
            role=User.Role.PATIENT,
        )
        PatientProfile.objects.create(
            user=user,
            date_of_birth=self.cleaned_data.get("date_of_birth"),
            gender=self.cleaned_data.get("gender", ""),
            address=self.cleaned_data.get("address", ""),
            emergency_contact=self.cleaned_data.get("emergency_contact", ""),
            medical_history=self.cleaned_data.get("medical_history", ""),
            allergies=self.cleaned_data.get("allergies", ""),
        )
        return user


class PatientForm(forms.Form):
    full_name = forms.CharField(max_length=300)
    email = forms.EmailField()
    phone = forms.CharField(max_length=30, required=False)
    gender = forms.ChoiceField(required=False, choices=[("", "---------")] + list(PatientProfile.Gender.choices))
    date_of_birth = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    address = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    emergency_contact = forms.CharField(max_length=150, required=False)
    medical_history = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}))
    allergies = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    is_active = forms.BooleanField(required=False, initial=True)

    def __init__(self, *args, instance=None, **kwargs):
        self.instance = instance
        initial = kwargs.pop("initial", {})
        if instance:
            initial.update(
                {
                    "full_name": instance.user.full_name,
                    "email": instance.user.email,
                    "phone": instance.user.phone,
                    "gender": instance.gender,
                    "date_of_birth": instance.date_of_birth,
                    "address": instance.address,
                    "emergency_contact": instance.emergency_contact,
                    "medical_history": instance.medical_history,
                    "allergies": instance.allergies,
                    "is_active": instance.user.is_active,
                }
            )
        super().__init__(*args, initial=initial, **kwargs)

    def clean_full_name(self):
        full_name = " ".join(self.cleaned_data["full_name"].split())
        if len(full_name.split()) < 2:
            raise forms.ValidationError("Enter first and last name.")
        return full_name

    def clean_email(self):
        email = get_user_model().objects.normalize_email(self.cleaned_data["email"]).lower()
        existing = get_user_model().objects.filter(email=email)
        if self.instance:
            existing = existing.exclude(pk=self.instance.user_id)
        if existing.exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        allowed = set("+()-. 0123456789")
        if phone and any(character not in allowed for character in phone):
            raise forms.ValidationError("Enter a valid phone number.")
        return phone

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get("date_of_birth")
        if date_of_birth and date_of_birth > timezone.localdate():
            raise forms.ValidationError("Date of birth cannot be in the future.")
        return date_of_birth

    @transaction.atomic
    def save(self):
        first_name, last_name = self.cleaned_data["full_name"].split(" ", 1)
        if self.instance:
            profile = self.instance
            user = profile.user
        else:
            user = User(role=User.Role.PATIENT)
            user.set_password(get_random_string(32))
            profile = PatientProfile(user=user)

        user.first_name = first_name
        user.last_name = last_name
        user.email = self.cleaned_data["email"]
        user.phone = self.cleaned_data["phone"]
        user.role = User.Role.PATIENT
        user.is_active = self.cleaned_data.get("is_active", False)
        user.save()

        profile.date_of_birth = self.cleaned_data.get("date_of_birth")
        profile.gender = self.cleaned_data.get("gender", "")
        profile.address = self.cleaned_data.get("address", "")
        profile.emergency_contact = self.cleaned_data.get("emergency_contact", "")
        profile.medical_history = self.cleaned_data.get("medical_history", "")
        profile.allergies = self.cleaned_data.get("allergies", "")
        profile.save()
        return profile
