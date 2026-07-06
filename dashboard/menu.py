from django.urls import NoReverseMatch, reverse

from accounts.models import User


ADMIN_USER_URLS = {
    "admin_users",
    "admin_user_add",
    "admin_user_detail",
    "admin_user_edit",
    "admin_user_reset_password",
    "admin_user_delete",
}


ARTICLE_DASHBOARD_URL_NAMES = {
    "articles_list",
    "articles_categories",
    "articles_category_edit",
    "articles_category_delete",
    "articles_create",
    "articles_image_upload",
    "articles_preview",
    "articles_edit",
    "articles_delete",
    "articles_toggle",
    "articles_comments",
    "articles_comment_approve",
    "articles_comment_reply",
    "articles_comment_delete",
}


ROLE_MENUS = {
    User.Role.ADMIN: [
        {"label": "Dashboard", "icon": "dashboard", "url_name": "dashboard:admin", "active_url_names": {"admin"}},
        {"label": "Appointments", "icon": "calendar_month", "url_name": "appointments:list", "active_namespaces": {"appointments"}},
        {"label": "Patients", "icon": "groups", "url_name": "patients:list", "active_namespaces": {"patients"}},
        {"label": "Dentists/Doctors", "icon": "medical_services", "url_name": "dentists:list", "active_namespaces": {"dentists"}},
        {"label": "Users Management", "icon": "manage_accounts", "url_name": "dashboard:admin_users", "active_url_names": ADMIN_USER_URLS},
        {"label": "Services Management", "icon": "category", "url_name": "services:list", "active_namespaces": {"services"}},
        {"label": "Ask Doctor Inbox", "icon": "mark_unread_chat_alt", "url_name": "ask_doctor:inbox", "active_namespaces": {"ask_doctor"}},
        {"label": "Dental Articles", "icon": "article", "url_name": "dashboard:articles_list", "active_url_names": ARTICLE_DASHBOARD_URL_NAMES},
        {"label": "Notifications / SMS & WhatsApp Logs", "icon": "mark_chat_read", "url_name": "notifications:logs", "active_namespaces": {"notifications"}},
        {"label": "Follow-ups", "icon": "next_plan", "url_name": "followups:list", "active_namespaces": {"followups"}},
        {"label": "Reports", "icon": "analytics", "url_name": "reports:list", "active_namespaces": {"reports"}},
        {"label": "Settings", "icon": "settings", "url_name": "clinic_settings:settings", "active_namespaces": {"clinic_settings"}},
    ],
    User.Role.DENTIST: [
        {"label": "Dashboard", "icon": "dashboard", "url_name": "dashboard:dentist", "active_url_names": {"dentist"}},
        {"label": "My Appointments", "icon": "calendar_month", "url_name": "dashboard:dentist_my_appointments", "active_url_names": {"dentist_my_appointments", "dentist_appointment_detail"}},
        {"label": "My Patients", "icon": "groups", "url_name": "dashboard:dentist_my_patients", "active_url_names": {"dentist_my_patients", "dentist_patient_detail"}},
        {"label": "Ask Doctor Inbox", "icon": "mark_unread_chat_alt", "url_name": "dashboard:dentist_ask_doctor", "active_url_names": {"dentist_ask_doctor"}},
        {"label": "Dental Articles", "icon": "article", "url_name": "dashboard:articles_list", "active_url_names": ARTICLE_DASHBOARD_URL_NAMES},
        {"label": "Notifications", "icon": "notifications", "url_name": "dashboard:dentist_notifications", "active_url_names": {"dentist_notifications"}},
        {"label": "Follow-ups", "icon": "next_plan", "url_name": "dashboard:dentist_followups", "active_url_names": {"dentist_followups", "dentist_followup_edit"}},
    ],
    User.Role.RECEPTIONIST: [
        {"label": "Dashboard", "icon": "dashboard", "url_name": "dashboard:receptionist", "active_url_names": {"receptionist"}},
        {"label": "Appointments", "icon": "calendar_month", "url_name": "dashboard:receptionist_appointments", "active_url_names": {"receptionist_appointments"}},
        {"label": "Dentist Availability", "icon": "event_available", "url_name": "dashboard:receptionist_dentist_availability", "active_url_names": {"receptionist_dentist_availability"}},
        {"label": "Patients", "icon": "groups", "url_name": "patients:list", "active_namespaces": {"patients"}},
        {"label": "Dental Articles", "icon": "article", "url_name": "dashboard:articles_list", "active_url_names": ARTICLE_DASHBOARD_URL_NAMES},
        {"label": "Notifications", "icon": "notifications", "url_name": "dashboard:receptionist_notifications", "active_url_names": {"receptionist_notifications"}},
        {"label": "Follow-ups", "icon": "next_plan", "url_name": "followups:list", "active_namespaces": {"followups"}},
    ],
    User.Role.PATIENT: [
        {"label": "Dashboard", "icon": "dashboard", "url_name": "dashboard:patient", "active_url_names": {"patient"}},
        {"label": "My Appointments", "icon": "calendar_month", "url_name": "dashboard:patient_appointments", "active_url_names": {"patient_appointments", "patient_book"}},
        {"label": "Ask Doctor Chat", "icon": "chat", "url_name": "ask_doctor:landing", "active_namespaces": {"ask_doctor"}},
        {"label": "My Notifications", "icon": "notifications", "url_name": "dashboard:patient_notifications", "active_url_names": {"patient_notifications"}},
        {"label": "My Profile", "icon": "person", "url_name": "dashboard:patient_profile", "active_url_names": {"patient_profile"}},
    ],
}


ROLE_LABELS = {
    User.Role.ADMIN: "Admin Dashboard",
    User.Role.DENTIST: "Dentist Dashboard",
    User.Role.RECEPTIONIST: "Front Desk",
    User.Role.PATIENT: "Patient Portal",
}


def _role_for_user(user):
    if not getattr(user, "is_authenticated", False):
        return None
    if user.is_superuser:
        return User.Role.ADMIN
    return getattr(user, "role", None)


def _is_active(item, resolver_match):
    if not resolver_match:
        return False
    if resolver_match.namespace in item.get("active_namespaces", set()):
        return True
    return resolver_match.url_name in item.get("active_url_names", set())


def get_dashboard_menu(user, request=None):
    role = _role_for_user(user)
    resolver_match = getattr(request, "resolver_match", None) if request else None
    menu = []

    for item in ROLE_MENUS.get(role, []):
        try:
            href = reverse(item["url_name"])
        except NoReverseMatch:
            continue
        menu.append(
            {
                "label": item["label"],
                "icon": item["icon"],
                "href": href,
                "is_active": _is_active(item, resolver_match),
            }
        )
    return menu


def get_dashboard_role_label(user):
    return ROLE_LABELS.get(_role_for_user(user), "Dashboard")
