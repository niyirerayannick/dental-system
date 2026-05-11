from django.contrib import admin

from .models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("patient", "appointment", "amount", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("patient__user__first_name", "patient__user__last_name", "patient__user__email")
