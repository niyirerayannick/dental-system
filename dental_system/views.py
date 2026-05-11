from django.shortcuts import redirect


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard:redirect")
    return redirect("accounts:login")
