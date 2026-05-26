from django.contrib.auth import authenticate
from django.test import TestCase

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

    def test_can_authenticate_when_phone_kwarg_is_used(self):
        user = authenticate(phone="+250788769140", password="StrongPass123")
        self.assertEqual(user, self.user)

    def test_rejects_wrong_password(self):
        user = authenticate(username="yan@example.com", password="wrong-password")
        self.assertIsNone(user)
