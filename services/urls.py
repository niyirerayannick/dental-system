from django.urls import path
from .views import (
    category_delete, category_json, category_list, category_toggle, category_update,
    service_delete, service_detail_api, service_image_delete, service_json, service_list,
    service_list_api, service_toggle, service_update,
)

app_name = "services"

urlpatterns = [
    # Services
    path("", service_list, name="list"),
    path("<int:pk>/json/", service_json, name="json"),
    path("<int:pk>/update/", service_update, name="update"),
    path("<int:pk>/toggle/", service_toggle, name="toggle"),
    path("<int:pk>/delete/", service_delete, name="delete"),
    path("images/<int:pk>/delete/", service_image_delete, name="image_delete"),
    # Categories
    path("categories/", category_list, name="categories"),
    path("categories/<int:pk>/json/", category_json, name="category_json"),
    path("categories/<int:pk>/update/", category_update, name="category_update"),
    path("categories/<int:pk>/toggle/", category_toggle, name="category_toggle"),
    path("categories/<int:pk>/delete/", category_delete, name="category_delete"),
    # Public API
    path("api/", service_list_api, name="api_list"),
    path("api/<int:pk>/", service_detail_api, name="api_detail"),
]
