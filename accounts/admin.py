from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .forms import UserAdminChangeForm, UserAdminCreationForm
from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = UserAdminCreationForm
    form = UserAdminChangeForm
    model = User

    list_display = ("phone", "email", "full_name", "role", "is_active", "is_staff", "date_joined")
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("phone", "email", "first_name", "last_name")
    ordering = ("last_name", "first_name")
    readonly_fields = ("date_joined", "last_login")

    fieldsets = (
        ("Login", {"fields": ("phone", "email", "password")}),
        ("Personal information", {"fields": ("first_name", "last_name", "role")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            "Create user",
            {
                "classes": ("wide",),
                "fields": (
                    "phone",
                    "email",
                    "first_name",
                    "last_name",
                    "role",
                    "password1",
                    "password2",
                    "is_active",
                    "is_staff",
                ),
            },
        ),
    )
