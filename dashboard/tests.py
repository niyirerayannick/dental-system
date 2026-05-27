from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from appointments.models import Appointment
from dashboard.menu import get_dashboard_menu
from dentists.models import DentistProfile
from patients.models import PatientProfile


@override_settings(SECURE_SSL_REDIRECT=False)
class AdminUserManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            phone="0780000001",
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            password="AdminPass123",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.client.force_login(self.admin)

    def test_admin_can_open_user_management(self):
        response = self.client.get(reverse("dashboard:admin_users"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "User management")
        self.assertContains(response, reverse("dashboard:admin_user_add"))
        self.assertNotContains(response, "Temporary password")

    def test_admin_can_create_user(self):
        response = self.client.post(
            reverse("dashboard:admin_user_add"),
            {
                "first_name": "Reception",
                "last_name": "Desk",
                "phone": "0780000002",
                "email": "",
                "role": User.Role.RECEPTIONIST,
                "is_active": "on",
                "password1": "NewUserPass123",
                "password2": "NewUserPass123",
            },
        )
        self.assertRedirects(response, reverse("dashboard:admin_users"))
        user = User.objects.get(phone="+250780000002")
        self.assertEqual(user.role, User.Role.RECEPTIONIST)
        self.assertIsNone(user.email)
        self.assertTrue(user.check_password("NewUserPass123"))

    def test_admin_can_update_user_information(self):
        user = User.objects.create_user(
            phone="0780000003",
            first_name="Old",
            last_name="Name",
            password="OldPass123",
            role=User.Role.PATIENT,
        )
        response = self.client.post(
            reverse("dashboard:admin_user_edit", args=[user.pk]),
            {
                "first_name": "New",
                "last_name": "Name",
                "phone": "0780000004",
                "email": "new@example.com",
                "role": User.Role.PATIENT,
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("dashboard:admin_users"))
        user.refresh_from_db()
        self.assertEqual(user.first_name, "New")
        self.assertEqual(user.phone, "+250780000004")
        self.assertEqual(user.email, "new@example.com")

    def test_admin_can_view_user_details(self):
        user = User.objects.create_user(
            phone="0780000006",
            first_name="View",
            last_name="Me",
            email="view@example.com",
            password="ViewPass123",
            role=User.Role.PATIENT,
        )
        response = self.client.get(reverse("dashboard:admin_user_detail", args=[user.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "View Me")
        self.assertContains(response, "view@example.com")

    def test_admin_can_reset_user_password(self):
        user = User.objects.create_user(
            phone="0780000005",
            first_name="Reset",
            last_name="Me",
            password="OldPass123",
            role=User.Role.PATIENT,
        )
        response = self.client.post(
            reverse("dashboard:admin_user_reset_password", args=[user.pk]),
            {
                "new_password1": "ResetPass123",
                "new_password2": "ResetPass123",
            },
        )
        self.assertRedirects(response, reverse("dashboard:admin_users"))
        user.refresh_from_db()
        self.assertTrue(user.check_password("ResetPass123"))

    def test_admin_can_delete_user(self):
        user = User.objects.create_user(
            phone="0780000007",
            first_name="Delete",
            last_name="Me",
            password="DeletePass123",
            role=User.Role.PATIENT,
        )
        response = self.client.post(reverse("dashboard:admin_user_delete", args=[user.pk]))
        self.assertRedirects(response, reverse("dashboard:admin_users"))
        self.assertFalse(User.objects.filter(pk=user.pk).exists())

    def test_admin_cannot_delete_self(self):
        response = self.client.post(reverse("dashboard:admin_user_delete", args=[self.admin.pk]))
        self.assertRedirects(response, reverse("dashboard:admin_users"))
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())


@override_settings(SECURE_SSL_REDIRECT=False)
class DashboardSidebarMenuTests(TestCase):
    def make_user(self, role, phone, **extra):
        defaults = {
            "first_name": role.title(),
            "last_name": "User",
            "password": "StrongPass123",
            "role": role,
        }
        defaults.update(extra)
        return User.objects.create_user(phone=phone, **defaults)

    def labels_for(self, user):
        return [item["label"] for item in get_dashboard_menu(user)]

    def assert_no_hidden_billing_or_treatments(self, labels):
        joined = " ".join(labels).lower()
        self.assertNotIn("billing", joined)
        self.assertNotIn("treatment", joined)

    def test_admin_sidebar_structure(self):
        user = self.make_user(User.Role.ADMIN, "0781000001", is_staff=True)
        labels = self.labels_for(user)
        self.assertEqual(
            labels,
            [
                "Dashboard",
                "Appointments",
                "Patients",
                "Dentists/Doctors",
                "Users Management",
                "Services Management",
                "Ask Doctor Inbox",
                "Dental Articles",
                "Notifications / SMS & WhatsApp Logs",
                "Follow-ups",
                "Reports",
                "Settings",
            ],
        )
        self.assert_no_hidden_billing_or_treatments(labels)

    def test_dentist_sidebar_structure(self):
        user = self.make_user(User.Role.DENTIST, "0781000002")
        labels = self.labels_for(user)
        self.assertEqual(
            labels,
            [
                "Dashboard",
                "My Appointments",
                "My Patients",
                "Ask Doctor Inbox",
                "My Dental Articles",
                "Notifications",
                "Follow-ups",
            ],
        )
        self.assert_no_hidden_billing_or_treatments(labels)
        self.assertTrue(all("#" not in item["href"] for item in get_dashboard_menu(user)))

    def test_receptionist_sidebar_structure(self):
        user = self.make_user(User.Role.RECEPTIONIST, "0781000003")
        labels = self.labels_for(user)
        self.assertEqual(labels, ["Dashboard", "Appointments", "Dentist Availability", "Patients", "Notifications", "Follow-ups"])
        self.assertNotIn("Ask Doctor Inbox", labels)
        self.assert_no_hidden_billing_or_treatments(labels)

    def test_patient_sidebar_structure(self):
        user = self.make_user(User.Role.PATIENT, "0781000004")
        labels = self.labels_for(user)
        self.assertEqual(labels, ["Dashboard", "My Appointments", "Ask Doctor Chat", "My Notifications", "My Profile"])
        self.assert_no_hidden_billing_or_treatments(labels)

    def test_role_dashboard_pages_render_shared_sidebar(self):
        cases = [
            (self.make_user(User.Role.ADMIN, "0781000008", is_staff=True), "dashboard:admin", "Users Management"),
            (self.make_user(User.Role.DENTIST, "0781000009"), "dashboard:dentist", "My Dental Articles"),
            (self.make_user(User.Role.RECEPTIONIST, "0781000010"), "dashboard:receptionist", "Appointments"),
            (self.make_user(User.Role.PATIENT, "0781000011"), "dashboard:patient", "Ask Doctor Chat"),
        ]
        for user, url_name, expected_label in cases:
            self.client.force_login(user)
            response = self.client.get(reverse(url_name))
            self.assertEqual(response.status_code, 200, url_name)
            self.assertContains(response, expected_label)

    def test_disallowed_direct_dashboard_urls_are_forbidden(self):
        receptionist = self.make_user(User.Role.RECEPTIONIST, "0781000005")
        self.client.force_login(receptionist)
        for name in ["notifications:logs", "reports:list", "dentists:list", "billing:list"]:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 403, name)

        dentist = self.make_user(User.Role.DENTIST, "0781000006")
        self.client.force_login(dentist)
        response = self.client.get(reverse("appointments:list"))
        self.assertEqual(response.status_code, 403)

        patient = self.make_user(User.Role.PATIENT, "0781000007")
        self.client.force_login(patient)
        for name in ["dashboard:patient_treatments", "dashboard:patient_invoices", "treatments:list"]:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 403, name)

    def test_dentist_dashboard_permissions_and_related_data(self):
        dentist_user = self.make_user(User.Role.DENTIST, "0781000012")
        other_dentist_user = self.make_user(User.Role.DENTIST, "0781000013")
        dentist = DentistProfile.objects.get(user=dentist_user)
        dentist.license_number = "D-100"
        dentist.save(update_fields=["license_number"])
        other_dentist = DentistProfile.objects.get(user=other_dentist_user)
        other_dentist.license_number = "D-200"
        other_dentist.save(update_fields=["license_number"])
        patient_user = self.make_user(User.Role.PATIENT, "0781000014", first_name="Assigned", last_name="Patient")
        other_patient_user = self.make_user(User.Role.PATIENT, "0781000015", first_name="Other", last_name="Patient")
        patient = PatientProfile.objects.create(user=patient_user)
        other_patient = PatientProfile.objects.create(user=other_patient_user)
        appointment = Appointment.objects.create(
            patient=patient,
            dentist=dentist,
            appointment_date="2026-05-26",
            appointment_time="09:00",
            status=Appointment.Status.PENDING,
        )
        Appointment.objects.create(
            patient=other_patient,
            dentist=other_dentist,
            appointment_date="2026-05-26",
            appointment_time="10:00",
            status=Appointment.Status.PENDING,
        )

        self.client.force_login(dentist_user)
        response = self.client.get(reverse("dashboard:dentist"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard overview")

        response = self.client.get(reverse("dashboard:dentist_my_appointments"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My appointments")
        self.assertContains(response, str(patient))
        self.assertNotContains(response, str(other_patient))

        response = self.client.get(reverse("appointments:json", args=[appointment.pk]))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("patients:detail", args=[other_patient.pk]))
        self.assertEqual(response.status_code, 404)
        response = self.client.get(reverse("treatments:list"))
        self.assertEqual(response.status_code, 403)
