from django.contrib import admin
from .models import DentalService, ServiceCategory, ServiceImage

admin.site.register(ServiceCategory)


class ServiceImageInline(admin.TabularInline):
    model = ServiceImage
    extra = 1
    fields = ("image", "alt_text", "sort_order")


@admin.register(DentalService)
class DentalServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_active", "updated_at")
    list_filter = ("is_active", "category")
    search_fields = ("name", "short_description", "description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ServiceImageInline]


@admin.register(ServiceImage)
class ServiceImageAdmin(admin.ModelAdmin):
    list_display = ("service", "alt_text", "sort_order", "created_at")
    list_filter = ("service",)
    search_fields = ("service__name", "alt_text")
