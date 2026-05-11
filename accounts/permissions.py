from functools import wraps

from django.contrib.auth.mixins import AccessMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .models import User


ROLE_DASHBOARD_URLS = {
    User.Role.ADMIN: "dashboard:admin",
    User.Role.DENTIST: "dashboard:dentist",
    User.Role.RECEPTIONIST: "dashboard:receptionist",
    User.Role.PATIENT: "dashboard:patient",
}


def get_dashboard_url_for_user(user):
    dashboard_name = ROLE_DASHBOARD_URLS.get(getattr(user, "role", None), "dashboard:patient")
    return reverse(dashboard_name)


def get_safe_redirect_url(request, fallback_url):
    redirect_to = request.POST.get("next") or request.GET.get("next")
    if redirect_to and url_has_allowed_host_and_scheme(
        redirect_to,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect_to
    return fallback_url


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path(), login_url=reverse("accounts:login"))
            if not request.user.is_active:
                raise PermissionDenied
            if request.user.is_superuser or request.user.role in roles:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied

        return wrapped_view

    return decorator


class RoleRequiredMixin(AccessMixin):
    allowed_roles = ()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_active:
            raise PermissionDenied
        if request.user.is_superuser or request.user.role in self.allowed_roles:
            return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied
