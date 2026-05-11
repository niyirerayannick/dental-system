from django.contrib import admin

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("patient", "dentist", "appointment_date", "appointment_time", "status")
    list_filter = ("status", "appointment_date")
    search_fields = (
        "patient__user__first_name",
        "patient__user__last_name",
        "dentist__user__last_name",
        "reason",
    )
