from django.http import JsonResponse
from django.shortcuts import redirect, render


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard:redirect")

    featured_services = []
    try:
        from services.models import DentalService
        featured_services = list(
            DentalService.objects.filter(is_active=True).select_related("category")[:3]
        )
    except Exception:
        pass

    return render(request, "public/home.html", {"featured_services": featured_services})


def health(request):
    return JsonResponse({"status": "ok"})
