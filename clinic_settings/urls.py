from django.urls import path

from .views import settings_view

app_name = "clinic_settings"

urlpatterns = [
    path("", settings_view, name="settings"),
]
