from django.contrib import messages
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import User
from accounts.permissions import role_required
from .forms import DentalServiceForm, ServiceCategoryForm
from .models import DentalService, ServiceCategory, ServiceImage


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


def _save_service_images(service, files):
    files = [file for file in files if file]
    start_order = service.gallery_images.count()
    for offset, image in enumerate(files):
        ServiceImage.objects.create(
            service=service,
            image=image,
            sort_order=start_order + offset,
            alt_text=service.name,
        )


def _service_image_url(service):
    image = service.primary_image
    return image.url if image else ""


# ── Public API (no auth) ─────────────────────────────────────────────────────

def service_list_api(request):
    """Return active services as JSON for the booking form."""
    services = (
        DentalService.objects.filter(is_active=True)
        .select_related("category")
        .values("id", "name", "category__name", "icon", "description", "short_description")
    )
    return JsonResponse({"services": list(services)})


def service_detail_api(request, pk):
    """Return a single service's details as JSON."""
    svc = get_object_or_404(DentalService.objects.filter(is_active=True), pk=pk)
    return JsonResponse({
        "id": svc.pk,
        "name": svc.name,
        "category": svc.category.name,
        "icon": svc.icon,
        "description": svc.short_description or svc.description,
    })


# ── Services CRUD ─────────────────────────────────────────────────────────────

@role_required(User.Role.ADMIN)
def service_list(request):
    q = request.GET.get("q", "").strip()
    cat_filter = request.GET.get("category", "")
    status_filter = request.GET.get("status", "")

    qs = DentalService.objects.select_related("category").prefetch_related("gallery_images")
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
        form = DentalServiceForm(request.POST, request.FILES)
        modal_open = True
        if form.is_valid():
            service = form.save()
            _save_service_images(service, request.FILES.getlist("images"))
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
    form = DentalServiceForm(request.POST, request.FILES, instance=svc)
    if form.is_valid():
        service = form.save()
        _save_service_images(service, request.FILES.getlist("images"))
        messages.success(request, "Service updated successfully.")
    else:
        messages.error(request, "Could not save service. Please check the form.")
    return redirect("services:list")


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


@require_POST
@role_required(User.Role.ADMIN)
def service_image_delete(request, pk):
    image = get_object_or_404(ServiceImage, pk=pk)
    image.delete()
    messages.success(request, "Service image removed.")
    return redirect("services:list")


@role_required(User.Role.ADMIN)
def service_json(request, pk):
    svc = get_object_or_404(
        DentalService.objects.select_related("category").prefetch_related("gallery_images"),
        pk=pk,
    )
    images = [
        {
            "id": image.pk,
            "url": image.image.url,
            "alt_text": image.alt_text or svc.name,
        }
        for image in svc.gallery_images.all()
        if image.image
    ]
    return JsonResponse({
        "ok": True,
        "record": {
            "id": svc.pk,
            "name": svc.name,
            "category": svc.category_id,
            "short_description": svc.short_description,
            "description": svc.description,
            "full_description": svc.full_description,
            "icon": svc.icon,
            "is_active": svc.is_active,
            "image_url": _service_image_url(svc),
            "images": images,
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


@role_required(User.Role.ADMIN)
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
