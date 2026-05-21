from django.contrib import messages
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import User
from accounts.permissions import role_required
from .forms import DentalServiceForm, ServiceCategoryForm
from .models import DentalService, ServiceCategory


def _ctx():
    return {
        "base_template": "dashboard/base.html",
        "active_nav": "services",
    }


def _service_kpis():
    total = DentalService.objects.count()
    active = DentalService.objects.filter(is_active=True).count()
    categories = ServiceCategory.objects.count()
    active_cats = ServiceCategory.objects.filter(is_active=True).count()
    return [
        {"label": "Total Services", "value": total, "icon": "medical_services"},
        {"label": "Active Services", "value": active, "icon": "check_circle"},
        {"label": "Categories", "value": categories, "icon": "category"},
        {"label": "Active Categories", "value": active_cats, "icon": "verified"},
    ]


# ── Public API (no auth) ─────────────────────────────────────────────────────

def service_list_api(request):
    """Return active services as JSON for the booking form."""
    services = (
        DentalService.objects.filter(is_active=True)
        .select_related("category")
        .values("id", "name", "category__name", "duration_minutes", "base_price", "icon", "description")
    )
    return JsonResponse({"services": list(services)})


def service_detail_api(request, pk):
    """Return a single service's details as JSON."""
    svc = get_object_or_404(DentalService.objects.filter(is_active=True), pk=pk)
    return JsonResponse({
        "id": svc.pk,
        "name": svc.name,
        "category": svc.category.name,
        "duration_minutes": svc.duration_minutes,
        "base_price": str(svc.base_price),
        "icon": svc.icon,
        "description": svc.description,
    })


# ── Services CRUD ─────────────────────────────────────────────────────────────

@role_required(User.Role.ADMIN)
def service_list(request):
    q = request.GET.get("q", "").strip()
    cat_filter = request.GET.get("category", "")
    status_filter = request.GET.get("status", "")

    qs = DentalService.objects.select_related("category")
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if cat_filter:
        qs = qs.filter(category_id=cat_filter)
    if status_filter == "active":
        qs = qs.filter(is_active=True)
    elif status_filter == "inactive":
        qs = qs.filter(is_active=False)

    form = DentalServiceForm()
    modal_open = False
    if request.method == "POST":
        form = DentalServiceForm(request.POST)
        modal_open = True
        if form.is_valid():
            form.save()
            messages.success(request, "Service created successfully.")
            return redirect("services:list")

    ctx = _ctx()
    ctx.update({
        "services": qs,
        "form": form,
        "modal_open": modal_open,
        "kpis": _service_kpis(),
        "categories": ServiceCategory.objects.all(),
        "filters": {"q": q, "category": cat_filter, "status": status_filter},
    })
    return render(request, "services/service_list.html", ctx)


@require_POST
@role_required(User.Role.ADMIN)
def service_update(request, pk):
    svc = get_object_or_404(DentalService, pk=pk)
    form = DentalServiceForm(request.POST, instance=svc)
    if form.is_valid():
        svc = form.save()
        return JsonResponse({"ok": True, "message": "Service updated."})
    return JsonResponse({"ok": False, "errors": form.errors}, status=400)


@require_POST
@role_required(User.Role.ADMIN)
def service_toggle(request, pk):
    svc = get_object_or_404(DentalService, pk=pk)
    svc.is_active = not svc.is_active
    svc.save(update_fields=["is_active"])
    status = "activated" if svc.is_active else "deactivated"
    messages.success(request, f"Service {status}.")
    return redirect("services:list")


@require_POST
@role_required(User.Role.ADMIN)
def service_delete(request, pk):
    get_object_or_404(DentalService, pk=pk).delete()
    messages.success(request, "Service deleted.")
    return redirect("services:list")


def service_json(request, pk):
    svc = get_object_or_404(DentalService.objects.select_related("category"), pk=pk)
    return JsonResponse({
        "ok": True,
        "record": {
            "id": svc.pk,
            "name": svc.name,
            "category": svc.category_id,
            "description": svc.description,
            "duration_minutes": svc.duration_minutes,
            "base_price": str(svc.base_price),
            "icon": svc.icon,
            "is_active": svc.is_active,
        },
    })


# ── Categories CRUD ───────────────────────────────────────────────────────────

@role_required(User.Role.ADMIN)
def category_list(request):
    q = request.GET.get("q", "").strip()
    qs = ServiceCategory.objects.annotate(service_count=Count("services"))
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))

    form = ServiceCategoryForm()
    modal_open = False
    if request.method == "POST":
        form = ServiceCategoryForm(request.POST)
        modal_open = True
        if form.is_valid():
            form.save()
            messages.success(request, "Category created successfully.")
            return redirect("services:categories")

    ctx = _ctx()
    ctx.update({
        "categories": qs,
        "form": form,
        "modal_open": modal_open,
        "kpis": _service_kpis(),
        "filters": {"q": q},
    })
    return render(request, "services/category_list.html", ctx)


@require_POST
@role_required(User.Role.ADMIN)
def category_update(request, pk):
    cat = get_object_or_404(ServiceCategory, pk=pk)
    form = ServiceCategoryForm(request.POST, instance=cat)
    if form.is_valid():
        cat = form.save()
        return JsonResponse({"ok": True, "message": "Category updated."})
    return JsonResponse({"ok": False, "errors": form.errors}, status=400)


@require_POST
@role_required(User.Role.ADMIN)
def category_toggle(request, pk):
    cat = get_object_or_404(ServiceCategory, pk=pk)
    cat.is_active = not cat.is_active
    cat.save(update_fields=["is_active"])
    status = "activated" if cat.is_active else "deactivated"
    messages.success(request, f"Category {status}.")
    return redirect("services:categories")


@require_POST
@role_required(User.Role.ADMIN)
def category_delete(request, pk):
    get_object_or_404(ServiceCategory, pk=pk).delete()
    messages.success(request, "Category deleted.")
    return redirect("services:categories")


def category_json(request, pk):
    cat = get_object_or_404(ServiceCategory, pk=pk)
    return JsonResponse({
        "ok": True,
        "record": {
            "id": cat.pk,
            "name": cat.name,
            "icon": cat.icon,
            "description": cat.description,
            "is_active": cat.is_active,
        },
    })
