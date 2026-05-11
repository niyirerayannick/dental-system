from django.urls import path

from .views import LoginPageView, logout_user, register

app_name = "accounts"

urlpatterns = [
    path("login/", LoginPageView.as_view(), name="login"),
    path("logout/", logout_user, name="logout"),
    path("register/", register, name="register"),
]
