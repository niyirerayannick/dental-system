from django.urls import path

from .views import log_list, mark_all_read, mark_read, resend_log

app_name = "notifications"

urlpatterns = [
    path("logs/", log_list, name="logs"),
    path("logs/<int:pk>/resend/", resend_log, name="resend_log"),
    path("<int:pk>/read/", mark_read, name="mark_read"),
    path("mark-all-read/", mark_all_read, name="mark_all_read"),
]
