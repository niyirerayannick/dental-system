from django.urls import path

from .views import followup_delete, followup_list, followup_status

app_name = "followups"

urlpatterns = [
    path("", followup_list, name="list"),
    path("<int:pk>/status/<str:status>/", followup_status, name="status"),
    path("<int:pk>/delete/", followup_delete, name="delete"),
]
