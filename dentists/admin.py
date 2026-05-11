from django.contrib import admin

from .models import DentistProfile


@admin.register(DentistProfile)
class DentistProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "specialization", "license_number", "available_days", "available_from", "available_to")
    list_filter = ("specialization",)
    search_fields = ("user__first_name", "user__last_name", "user__email", "license_number")
