from django.contrib import admin

from .models import Treatment


@admin.register(Treatment)
class TreatmentAdmin(admin.ModelAdmin):
    list_display = ("patient", "dentist", "appointment", "treatment_date")
    list_filter = ("treatment_date",)
    search_fields = (
        "patient__user__first_name",
        "patient__user__last_name",
        "dentist__user__last_name",
        "diagnosis",
    )
