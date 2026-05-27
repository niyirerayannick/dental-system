from django.contrib import admin

from .models import Notification, NotificationLog


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "notification_type", "is_read", "created_at")
    list_filter = ("notification_type", "is_read", "created_at")
    search_fields = ("title", "message", "user__phone", "user__first_name", "user__last_name")
    date_hierarchy = "created_at"


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "channel", "status", "phone_number", "patient", "appointment", "fallback_sent", "provider_sid")
    list_filter = ("channel", "status", "fallback_sent", "provider", "created_at")
    search_fields = (
        "phone_number",
        "message",
        "error_message",
        "provider_sid",
        "patient__user__first_name",
        "patient__user__last_name",
    )
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
