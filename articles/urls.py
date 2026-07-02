from django.urls import path

from .views import (
    article_comment,
    article_like,
    dashboard_article_create,
    dashboard_article_delete,
    dashboard_article_edit,
    dashboard_article_image_upload,
    dashboard_article_list,
    dashboard_article_preview,
    dashboard_article_toggle_publish,
    dashboard_category_delete,
    dashboard_category_edit,
    dashboard_category_list,
    dashboard_comment_approve,
    dashboard_comment_delete,
    dashboard_comment_list,
    dashboard_comment_reply,
    education_detail,
    education_list,
)

app_name = "articles"

urlpatterns = [
    # Public list (exact)
    path("", education_list, name="list"),
    # Dashboard article routes — must come before the slug catch-all
    path("dashboard/", dashboard_article_list, name="dashboard_list"),
    path("dashboard/categories/", dashboard_category_list, name="dashboard_categories"),
    path("dashboard/categories/<int:pk>/edit/", dashboard_category_edit, name="dashboard_category_edit"),
    path("dashboard/categories/<int:pk>/delete/", dashboard_category_delete, name="dashboard_category_delete"),
    path("dashboard/create/", dashboard_article_create, name="dashboard_create"),
    path("dashboard/image-upload/", dashboard_article_image_upload, name="image_upload"),
    path("dashboard/<int:pk>/preview/", dashboard_article_preview, name="dashboard_preview"),
    path("dashboard/<int:pk>/edit/", dashboard_article_edit, name="dashboard_edit"),
    path("dashboard/<int:pk>/delete/", dashboard_article_delete, name="dashboard_delete"),
    path("dashboard/<int:pk>/toggle/", dashboard_article_toggle_publish, name="dashboard_toggle"),
    # Dashboard comment management
    path("dashboard/comments/", dashboard_comment_list, name="dashboard_comments"),
    path("dashboard/comments/<int:pk>/approve/", dashboard_comment_approve, name="dashboard_comment_approve"),
    path("dashboard/comments/<int:pk>/reply/", dashboard_comment_reply, name="dashboard_comment_reply"),
    path("dashboard/comments/<int:pk>/delete/", dashboard_comment_delete, name="dashboard_comment_delete"),
    # Public engagement endpoints
    path("<int:pk>/like/", article_like, name="like"),
    path("<slug:slug>/comment/", article_comment, name="comment"),
    # Public detail — slug catch-all must be last
    path("<slug:slug>/", education_detail, name="detail"),
]
