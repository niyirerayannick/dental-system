from django import forms
from django.contrib.auth.forms import AuthenticationForm, ReadOnlyPasswordHashField, UserCreationForm

from .models import User

_TEXT_INPUT  = "pl-12 h-12"
_PASS_INPUT  = "pl-12 pr-12 h-12"


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(attrs={"placeholder": "you@example.com", "class": _TEXT_INPUT}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "••••••••", "class": _PASS_INPUT}),
    )

    def clean_username(self):
        return User.objects.normalize_email(self.cleaned_data["username"]).lower()


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(
        widget=forms.TextInput(attrs={"placeholder": "John", "class": _TEXT_INPUT}),
    )
    last_name = forms.CharField(
        widget=forms.TextInput(attrs={"placeholder": "Doe", "class": _TEXT_INPUT}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"placeholder": "you@example.com", "class": _TEXT_INPUT}),
    )
    phone = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "+250 7XX XXX XXX", "class": _TEXT_INPUT}),
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update({"placeholder": "••••••••", "class": _PASS_INPUT})
        self.fields["password2"].widget.attrs.update({"placeholder": "••••••••", "class": _PASS_INPUT})

    def clean_email(self):
        email = User.objects.normalize_email(self.cleaned_data["email"]).lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        allowed = set("+()-. 0123456789")
        if phone and any(character not in allowed for character in phone):
            raise forms.ValidationError("Enter a valid phone number.")
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.PATIENT
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class UserAdminCreationForm(UserCreationForm):
    def clean_email(self):
        return User.objects.normalize_email(self.cleaned_data["email"]).lower()

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "phone", "role", "is_active", "is_staff"]


class UserAdminChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = [
            "email",
            "password",
            "first_name",
            "last_name",
            "phone",
            "role",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        ]
