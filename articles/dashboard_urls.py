from django.urls import path

from .views import (
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
)

urlpatterns = [
    path("", dashboard_article_list, name="articles_list"),
    path("categories/", dashboard_category_list, name="articles_categories"),
    path("categories/<int:pk>/edit/", dashboard_category_edit, name="articles_category_edit"),
    path("categories/<int:pk>/delete/", dashboard_category_delete, name="articles_category_delete"),
    path("create/", dashboard_article_create, name="articles_create"),
    path("image-upload/", dashboard_article_image_upload, name="articles_image_upload"),
    path("<int:pk>/preview/", dashboard_article_preview, name="articles_preview"),
    path("<int:pk>/edit/", dashboard_article_edit, name="articles_edit"),
    path("<int:pk>/delete/", dashboard_article_delete, name="articles_delete"),
    path("<int:pk>/toggle/", dashboard_article_toggle_publish, name="articles_toggle"),
    path("comments/", dashboard_comment_list, name="articles_comments"),
    path("comments/<int:pk>/approve/", dashboard_comment_approve, name="articles_comment_approve"),
    path("comments/<int:pk>/reply/", dashboard_comment_reply, name="articles_comment_reply"),
    path("comments/<int:pk>/delete/", dashboard_comment_delete, name="articles_comment_delete"),
]
