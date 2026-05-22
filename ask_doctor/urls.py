from django.urls import path

from .views import (
    ask_form,
    close_conversation,
    conversation_detail,
    conversation_list,
    inbox,
    inbox_detail,
    landing,
    new_conversation,
)

app_name = "ask_doctor"

urlpatterns = [
    # Patient-facing
    path("", landing, name="landing"),
    path("conversations/", conversation_list, name="conversation_list"),
    path("conversations/new/", new_conversation, name="new_conversation"),
    path("conversations/<int:pk>/", conversation_detail, name="conversation_detail"),
    path("conversations/<int:pk>/close/", close_conversation, name="close_conversation"),
    path("form/", ask_form, name="ask_form"),
    # Staff inbox
    path("inbox/", inbox, name="inbox"),
    path("inbox/<int:pk>/", inbox_detail, name="inbox_detail"),
]
