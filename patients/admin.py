from django.contrib import admin

from .models import PatientProfile


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "date_of_birth", "gender", "emergency_contact")
    list_filter = ("gender",)
    search_fields = ("user__first_name", "user__last_name", "user__email", "emergency_contact")
