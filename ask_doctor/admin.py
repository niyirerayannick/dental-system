from django.contrib import admin

from .models import DoctorConversation, DoctorMessage


class DoctorMessageInline(admin.TabularInline):
    model = DoctorMessage
    extra = 0
    readonly_fields = ("sender", "message", "attachment", "is_read", "created_at")
    can_delete = False


@admin.register(DoctorConversation)
class DoctorConversationAdmin(admin.ModelAdmin):
    list_display = ("pk", "patient", "subject", "assigned_doctor", "status", "created_at", "updated_at")
    list_filter = ("status", "created_at")
    search_fields = ("patient__email", "patient__first_name", "subject")
    readonly_fields = ("created_at", "updated_at")
    inlines = [DoctorMessageInline]
    actions = ["mark_closed"]

    def mark_closed(self, request, queryset):
        queryset.update(status=DoctorConversation.Status.CLOSED)
    mark_closed.short_description = "Mark selected conversations as closed"


@admin.register(DoctorMessage)
class DoctorMessageAdmin(admin.ModelAdmin):
    list_display = ("pk", "conversation", "sender", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("sender__email", "message")
    readonly_fields = ("created_at",)
