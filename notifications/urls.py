from django.urls import path

from .views import mark_all_read, mark_read

app_name = "notifications"

urlpatterns = [
    path("<int:pk>/read/", mark_read, name="mark_read"),
    path("mark-all-read/", mark_all_read, name="mark_all_read"),
]
