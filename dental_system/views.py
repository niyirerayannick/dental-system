from django.http import JsonResponse
from django.shortcuts import redirect, render


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard:redirect")

    featured_services = []
    footer_services = []
    try:
        from services.models import DentalService
        qs = DentalService.objects.filter(is_active=True).select_related("category")
        featured_services = list(qs[:3])
        footer_services = list(qs[3:8])
    except Exception:
        pass

    return render(request, "public/home.html", {
        "featured_services": featured_services,
        "footer_services": footer_services,
    })


def health(request):
    return JsonResponse({"status": "ok"})
