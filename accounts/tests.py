from django.contrib.auth import authenticate
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import LoginForm
from .models import User


class EmailOrPhoneLoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="0788769140",
            email="yan@example.com",
            first_name="Yan",
            last_name="Niy",
            password="StrongPass123",
        )

    def test_can_authenticate_with_phone_and_password(self):
        user = authenticate(username="0788769140", password="StrongPass123")
        self.assertEqual(user, self.user)

    def test_can_authenticate_with_email_and_password(self):
        user = authenticate(username="YAN@example.com", password="StrongPass123")
        self.assertEqual(user, self.user)

    def test_can_authenticate_with_spaced_email_and_password(self):
        user = authenticate(username="  YAN@example.com  ", password="StrongPass123")
        self.assertEqual(user, self.user)

    def test_can_authenticate_when_email_kwarg_is_used(self):
        user = authenticate(email="YAN@example.com", password="StrongPass123")
        self.assertEqual(user, self.user)

    def test_can_authenticate_when_phone_kwarg_is_used(self):
        user = authenticate(phone="+250788769140", password="StrongPass123")
        self.assertEqual(user, self.user)

    def test_rejects_wrong_password(self):
        user = authenticate(username="yan@example.com", password="wrong-password")
        self.assertIsNone(user)

    def test_login_form_defaults_to_phone(self):
        form = LoginForm()
        self.assertEqual(form.fields["login_method"].initial, "phone")

    def test_login_form_accepts_email(self):
        form = LoginForm(data={"login_method": "email", "username": "YAN@example.com", "password": "StrongPass123"})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.get_user(), self.user)

    def test_login_form_accepts_phone_when_phone_is_selected(self):
        form = LoginForm(data={"login_method": "phone", "username": "0788769140", "password": "StrongPass123"})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.get_user(), self.user)

    def test_login_form_rejects_email_when_phone_is_selected(self):
        form = LoginForm(data={"login_method": "phone", "username": "yan@example.com", "password": "StrongPass123"})
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_login_form_rejects_phone_when_email_is_selected(self):
        form = LoginForm(data={"login_method": "email", "username": "0788769140", "password": "StrongPass123"})
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    @override_settings(SECURE_SSL_REDIRECT=False)
    def test_login_view_accepts_email(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"login_method": "email", "username": "YAN@example.com", "password": "StrongPass123"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)
