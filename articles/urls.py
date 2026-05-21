from django.urls import path

from .views import (
    dashboard_article_create,
    dashboard_article_delete,
    dashboard_article_edit,
    dashboard_article_image_upload,
    dashboard_article_list,
    dashboard_article_toggle_publish,
    education_detail,
    education_list,
)

app_name = "articles"

urlpatterns = [
    # Public list (exact)
    path("", education_list, name="list"),
    # Dashboard routes — must come before the slug catch-all
    path("dashboard/", dashboard_article_list, name="dashboard_list"),
    path("dashboard/create/", dashboard_article_create, name="dashboard_create"),
    path("dashboard/image-upload/", dashboard_article_image_upload, name="image_upload"),
    path("dashboard/<int:pk>/edit/", dashboard_article_edit, name="dashboard_edit"),
    path("dashboard/<int:pk>/delete/", dashboard_article_delete, name="dashboard_delete"),
    path("dashboard/<int:pk>/toggle/", dashboard_article_toggle_publish, name="dashboard_toggle"),
    # Public detail — slug catch-all must be last
    path("<slug:slug>/", education_detail, name="detail"),
]
