import json
import os

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import User
from accounts.permissions import role_required

from .forms import ArticleForm
from .models import Article, ArticleCategory


# ── Public views ──────────────────────────────────────────────────────────────

def education_list(request):
    category_slug = request.GET.get("category", "")
    categories = ArticleCategory.objects.all()
    articles = Article.objects.filter(is_published=True).select_related("category", "author")

    active_category = None
    if category_slug:
        active_category = get_object_or_404(ArticleCategory, slug=category_slug)
        articles = articles.filter(category=active_category)

    featured = articles.first()
    recent = articles[1:7] if featured else articles[:6]

    footer_services = []
    try:
        from services.models import DentalService
        footer_services = list(
            DentalService.objects.filter(is_active=True).select_related("category")[3:8]
        )
    except Exception:
        pass

    return render(request, "public/education.html", {
        "articles": articles,
        "featured": featured,
        "recent": recent,
        "categories": categories,
        "active_category": active_category,
        "footer_services": footer_services,
    })


def education_detail(request, slug):
    article = get_object_or_404(Article, slug=slug, is_published=True)
    related = (
        Article.objects.filter(is_published=True)
        .exclude(pk=article.pk)
        .filter(category=article.category)
        .select_related("category", "author")[:3]
    )

    footer_services = []
    try:
        from services.models import DentalService
        footer_services = list(
            DentalService.objects.filter(is_active=True).select_related("category")[3:8]
        )
    except Exception:
        pass

    return render(request, "public/education_detail.html", {
        "article": article,
        "related": related,
        "footer_services": footer_services,
    })


# ── Dashboard views ────────────────────────────────────────────────────────────

@role_required(User.Role.ADMIN, User.Role.DENTIST)
def dashboard_article_list(request):
    qs = Article.objects.select_related("category", "author").order_by("-created_at")

    # Dentists see only their own articles
    if request.user.role == User.Role.DENTIST:
        qs = qs.filter(author=request.user)

    q = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "")
    category_filter = request.GET.get("category", "")

    if q:
        qs = qs.filter(title__icontains=q)
    if status_filter == "published":
        qs = qs.filter(is_published=True)
    elif status_filter == "draft":
        qs = qs.filter(is_published=False)
    if category_filter:
        qs = qs.filter(category__slug=category_filter)

    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get("page"))

    categories = ArticleCategory.objects.all()

    is_dentist = request.user.role == User.Role.DENTIST

    return render(request, "dashboard/articles/list.html", {
        "articles": page,
        "page_obj": page,
        "q": q,
        "status_filter": status_filter,
        "category_filter": category_filter,
        "categories": categories,
        "total": qs.count(),
        "is_dentist": is_dentist,
    })


@role_required(User.Role.ADMIN, User.Role.DENTIST)
def dashboard_article_create(request):
    if request.method == "POST":
        form = ArticleForm(request.POST, request.FILES)
        if form.is_valid():
            article = form.save(commit=False)
            article.author = request.user
            article.save()
            messages.success(request, f'Article "{article.title}" created successfully.')
            return redirect("articles:dashboard_list")
    else:
        form = ArticleForm()

    return render(request, "dashboard/articles/create.html", {"form": form})


@role_required(User.Role.ADMIN, User.Role.DENTIST)
def dashboard_article_edit(request, pk):
    article = get_object_or_404(Article, pk=pk)

    # Dentists can only edit their own articles
    if request.user.role == User.Role.DENTIST and article.author != request.user:
        messages.error(request, "You do not have permission to edit this article.")
        return redirect("articles:dashboard_list")

    if request.method == "POST":
        form = ArticleForm(request.POST, request.FILES, instance=article)
        if form.is_valid():
            form.save()
            messages.success(request, f'Article "{article.title}" updated successfully.')
            return redirect("articles:dashboard_list")
    else:
        form = ArticleForm(instance=article)

    return render(request, "dashboard/articles/edit.html", {"form": form, "article": article})


@role_required(User.Role.ADMIN, User.Role.DENTIST)
def dashboard_article_delete(request, pk):
    article = get_object_or_404(Article, pk=pk)

    # Dentists can only delete their own articles
    if request.user.role == User.Role.DENTIST and article.author != request.user:
        messages.error(request, "You do not have permission to delete this article.")
        return redirect("articles:dashboard_list")

    if request.method == "POST":
        title = article.title
        article.delete()
        messages.success(request, f'Article "{title}" deleted.')
        return redirect("articles:dashboard_list")

    return render(request, "dashboard/articles/delete.html", {"article": article})


@role_required(User.Role.ADMIN, User.Role.DENTIST)
@require_POST
def dashboard_article_toggle_publish(request, pk):
    article = get_object_or_404(Article, pk=pk)

    if request.user.role == User.Role.DENTIST and article.author != request.user:
        messages.error(request, "You do not have permission to modify this article.")
        return redirect("articles:dashboard_list")

    article.is_published = not article.is_published
    article.save()
    state = "published" if article.is_published else "unpublished"
    messages.success(request, f'"{article.title}" {state}.')
    return redirect("articles:dashboard_list")


@role_required(User.Role.ADMIN, User.Role.DENTIST)
def dashboard_article_preview(request, pk):
    article = get_object_or_404(Article, pk=pk)

    # Dentists can only preview their own articles
    if request.user.role == User.Role.DENTIST and article.author != request.user:
        messages.error(request, "You do not have permission to preview this article.")
        return redirect("articles:dashboard_list")

    return render(request, "dashboard/articles/preview.html", {"article": article})


@role_required(User.Role.ADMIN, User.Role.DENTIST)
def dashboard_article_image_upload(request):
    """TinyMCE image upload endpoint."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    upload = request.FILES.get("file")
    if not upload:
        return JsonResponse({"error": "No file provided"}, status=400)

    # Validate it's an image
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml"}
    if upload.content_type not in allowed_types:
        return JsonResponse({"error": "Invalid file type"}, status=400)

    # Save to media/articles/uploads/
    from django.core.files.storage import default_storage
    from django.core.files.base import ContentFile

    filename = upload.name
    # Sanitize filename
    filename = os.path.basename(filename)
    path = default_storage.save(f"articles/uploads/{filename}", ContentFile(upload.read()))
    url = request.build_absolute_uri(f"/media/{path}")
    return JsonResponse({"location": url})
