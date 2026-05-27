from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from .forms import LoginForm, RegisterForm
from .permissions import get_dashboard_url_for_user, get_safe_redirect_url
from patients.models import PatientProfile


class LoginPageView(LoginView):
    authentication_form = LoginForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return get_safe_redirect_url(self.request, get_dashboard_url_for_user(self.request.user))


@csrf_protect
def register(request):
    if request.user.is_authenticated:
        return redirect(get_dashboard_url_for_user(request.user))

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            PatientProfile.objects.get_or_create(
                user=user,
                defaults={"preferred_language": form.cleaned_data.get("preferred_language") or PatientProfile.Language.KINYARWANDA},
            )
            login(request, user)
            messages.success(request, "Welcome! Your account has been created.")
            return redirect(get_safe_redirect_url(request, get_dashboard_url_for_user(user)))
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


@require_POST
def logout_user(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("home")
