from django.contrib import admin

from .models import FollowUp


@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ("patient", "followup_date", "reason", "status", "assigned_to", "created_at")
    list_filter = ("status", "followup_date")
    search_fields = ("patient__user__first_name", "patient__user__last_name", "reason")
    date_hierarchy = "followup_date"
