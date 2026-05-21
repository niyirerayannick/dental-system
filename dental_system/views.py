from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard:redirect")

    if request.method == "POST":
        messages.success(request, "Thank you! Your message has been received. We'll be in touch shortly.")
        return redirect("home")

    featured_services = []
    footer_services = []
    try:
        from services.models import DentalService
        qs = DentalService.objects.filter(is_active=True).select_related("category")
        featured_services = list(qs[:3])
        footer_services = list(qs[3:8])
    except Exception:
        pass

    dentists = []
    try:
        from dentists.models import DentistProfile
        dentists = list(
            DentistProfile.objects
            .filter(user__is_active=True, is_available=True)
            .select_related("user")
            .order_by("user__last_name", "user__first_name")
        )
    except Exception:
        pass

    return render(request, "public/home.html", {
        "featured_services": featured_services,
        "footer_services": footer_services,
        "dentists": dentists,
    })


def public_services(request):
    """Public-facing services listing grouped by category."""
    if request.user.is_authenticated:
        return redirect("dashboard:redirect")

    categories = []
    all_services = []
    try:
        from services.models import DentalService, ServiceCategory
        cats = ServiceCategory.objects.filter(is_active=True).prefetch_related(
            "services"
        )
        for cat in cats:
            svcs = list(cat.services.filter(is_active=True))
            if svcs:
                categories.append({"category": cat, "services": svcs})
        all_services = list(DentalService.objects.filter(is_active=True).select_related("category"))
    except Exception:
        pass

    footer_services = all_services[3:8]

    return render(request, "public/services.html", {
        "categories": categories,
        "all_services": all_services,
        "footer_services": footer_services,
    })


def public_book(request):
    """Public booking entry point — redirects to login then patient book page."""
    from django.conf import settings
    dentist_param = request.GET.get("dentist", "")
    next_url = "/dashboard/patient/book/"
    if dentist_param:
        next_url = f"/dashboard/patient/book/?dentist={dentist_param}"

    if request.user.is_authenticated:
        return redirect(next_url)

    from django.urls import reverse
    login_url = reverse("accounts:login")
    return redirect(f"{login_url}?next={next_url}")


def public_ask_doctor(request):
    """Public ask-a-doctor enquiry page."""
    if request.user.is_authenticated:
        return redirect("dashboard:redirect")

    if request.method == "POST":
        messages.success(
            request,
            "Your question has been submitted! One of our dentists will respond within 24 hours."
        )
        return redirect("pub_ask_doctor")

    dentists = []
    try:
        from dentists.models import DentistProfile
        dentists = list(
            DentistProfile.objects
            .filter(user__is_active=True, is_available=True)
            .select_related("user")
            .order_by("user__last_name", "user__first_name")
        )
    except Exception:
        pass

    footer_services = []
    try:
        from services.models import DentalService
        footer_services = list(DentalService.objects.filter(is_active=True).select_related("category")[3:8])
    except Exception:
        pass

    return render(request, "public/ask_doctor.html", {
        "dentists": dentists,
        "footer_services": footer_services,
    })



def public_contact(request):
    """Dedicated public contact page."""
    if request.user.is_authenticated:
        return redirect("dashboard:redirect")

    if request.method == "POST":
        messages.success(request, "Thank you! Your message has been received. We'll be in touch shortly.")
        return redirect("pub_contact")

    footer_services = []
    try:
        from services.models import DentalService
        footer_services = list(DentalService.objects.filter(is_active=True).select_related("category")[3:8])
    except Exception:
        pass

    return render(request, "public/contact.html", {
        "footer_services": footer_services,
    })


def health(request):
    return JsonResponse({"status": "ok"})
