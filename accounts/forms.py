import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, ReadOnlyPasswordHashField, SetPasswordForm, UserCreationForm
from django.core.validators import validate_email

from .models import User, normalize_phone

_BARE = (
    "h-full w-full rounded-none border-0 bg-transparent p-0 text-sm "
    "text-slate-900 shadow-none outline-none ring-0 "
    "focus:border-0 focus:outline-none focus:ring-0 focus:shadow-none"
)

_RWANDA_RE = re.compile(r'^(\+?250)?0?7\d{8}$')


def validate_rwanda_phone(value):
    digits = re.sub(r'[\s\-\(\)]', '', value)
    if not _RWANDA_RE.match(digits):
        raise forms.ValidationError(
            "Enter a valid Rwanda phone number (e.g. 0780474044 or +250780474044)."
        )


class LoginForm(AuthenticationForm):
    LOGIN_METHOD_EMAIL = "email"
    LOGIN_METHOD_PHONE = "phone"
    LOGIN_METHOD_CHOICES = (
        (LOGIN_METHOD_PHONE, "Phone number"),
        (LOGIN_METHOD_EMAIL, "Email"),
    )

    login_method = forms.ChoiceField(
        choices=LOGIN_METHOD_CHOICES,
        initial=LOGIN_METHOD_PHONE,
        widget=forms.RadioSelect,
    )
    username = forms.CharField(
        label="Phone number",
        widget=forms.TextInput(attrs={"placeholder": "0780474044", "class": _BARE, "autocomplete": "username", "inputmode": "tel"}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "••••••••", "class": _BARE}),
    )

    error_messages = {
        "invalid_login": "Please enter a correct email or phone number and password.",
        "inactive": "This account is inactive.",
    }

    def clean_username(self):
        return self.cleaned_data.get("username", "").strip()

    def clean(self):
        cleaned_data = self.cleaned_data
        raw = cleaned_data.get("username", "").strip()
        login_method = self.cleaned_data.get("login_method", self.LOGIN_METHOD_PHONE)

        if not raw:
            return super().clean()

        if login_method == self.LOGIN_METHOD_EMAIL:
            try:
                validate_email(raw)
            except forms.ValidationError:
                self.add_error("username", "Enter a valid email address.")
                return cleaned_data
            cleaned_data["username"] = User.objects.normalize_email(raw).lower()
        else:
            try:
                validate_rwanda_phone(raw)
            except forms.ValidationError as exc:
                self.add_error("username", exc)
                return cleaned_data
            cleaned_data["username"] = normalize_phone(raw)

        return super().clean()


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(
        widget=forms.TextInput(attrs={"placeholder": "John", "class": _BARE}),
    )
    last_name = forms.CharField(
        widget=forms.TextInput(attrs={"placeholder": "Doe", "class": _BARE}),
    )
    phone = forms.CharField(
        label="Phone number",
        validators=[validate_rwanda_phone],
        widget=forms.TextInput(attrs={"placeholder": "+250 7XX XXX XXX", "class": _BARE}),
    )
    email = forms.EmailField(
        required=False,
        label="Email address",
        widget=forms.EmailInput(attrs={"placeholder": "you@example.com (optional)", "class": _BARE}),
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone", "email", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update({"placeholder": "••••••••", "class": _BARE})
        self.fields["password2"].widget.attrs.update({"placeholder": "••••••••", "class": _BARE})

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data.get("phone", "").strip())
        if User.objects.filter(phone=phone).exists():
            raise forms.ValidationError("A user with this phone number already exists.")
        return phone

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        if not email:
            return None
        email = User.objects.normalize_email(email).lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.PATIENT
        user.phone = self.cleaned_data["phone"]
        user.email = self.cleaned_data.get("email") or None
        if commit:
            user.save()
        return user


class UserAdminCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["phone", "email", "first_name", "last_name", "role", "is_active", "is_staff"]

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        if not email:
            return None
        email = User.objects.normalize_email(email).lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data.get("phone", "").strip())
        if not phone:
            raise forms.ValidationError("Phone number is required.")
        if User.objects.filter(phone=phone).exists():
            raise forms.ValidationError("A user with this phone number already exists.")
        return phone


class UserAdminChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = [
            "phone",
            "email",
            "password",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        ]

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        if not email:
            return None
        email = User.objects.normalize_email(email).lower()
        qs = User.objects.filter(email=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data.get("phone", "").strip())
        if not phone:
            raise forms.ValidationError("Phone number is required.")
        qs = User.objects.filter(phone=phone)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A user with this phone number already exists.")
        return phone


class DashboardUserCreateForm(UserCreationForm):
    email = forms.EmailField(required=False, label="Email address (optional)")
    is_active = forms.BooleanField(required=False, initial=True)
    is_staff = forms.BooleanField(required=False)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone", "email", "role", "is_active", "is_staff", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "h-4 w-4 rounded border-gray-300 text-green-600 focus:ring-green-500")
            else:
                field.widget.attrs.setdefault("class", _BARE)
        self.fields["phone"].validators.append(validate_rwanda_phone)
        self.fields["password1"].widget.attrs.setdefault("placeholder", "Temporary password")
        self.fields["password2"].widget.attrs.setdefault("placeholder", "Confirm password")

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data.get("phone", "").strip())
        if not phone:
            raise forms.ValidationError("Phone number is required.")
        if User.objects.filter(phone=phone).exists():
            raise forms.ValidationError("A user with this phone number already exists.")
        return phone

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        if not email:
            return None
        email = User.objects.normalize_email(email).lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email


class DashboardUserUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=False, label="Email address (optional)")
    is_active = forms.BooleanField(required=False)
    is_staff = forms.BooleanField(required=False)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone", "email", "role", "is_active", "is_staff"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "h-4 w-4 rounded border-gray-300 text-green-600 focus:ring-green-500")
            else:
                field.widget.attrs.setdefault("class", _BARE)
        self.fields["phone"].validators.append(validate_rwanda_phone)

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data.get("phone", "").strip())
        if not phone:
            raise forms.ValidationError("Phone number is required.")
        qs = User.objects.filter(phone=phone)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A user with this phone number already exists.")
        return phone

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        if not email:
            return None
        email = User.objects.normalize_email(email).lower()
        qs = User.objects.filter(email=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email


class DashboardUserPasswordResetForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", _BARE)
