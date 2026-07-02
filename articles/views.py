import os
import uuid

from django.contrib import messages
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.utils.text import get_valid_filename
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import User
from accounts.permissions import role_required
from dental_system.upload_validation import validate_uploaded_image

from .forms import ArticleCategoryForm, ArticleForm, CommentForm, ReplyForm
from .models import Article, ArticleCategory, ArticleComment, ArticleLike, ArticleView


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")


def _ensure_session_key(request):
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


# ── Public views ────────────────────────────────────────────────────────────────

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

    # ── Track view (once per session / once per user) ─────────────────────────
    session_key = _ensure_session_key(request)
    ip = _get_client_ip(request)
    if request.user.is_authenticated:
        if not ArticleView.objects.filter(article=article, user=request.user).exists():
            ArticleView.objects.create(
                article=article, user=request.user,
                session_key=session_key, ip_address=ip,
            )
    else:
        if not ArticleView.objects.filter(article=article, session_key=session_key).exists():
            ArticleView.objects.create(
                article=article, session_key=session_key, ip_address=ip,
            )

    # ── Engagement counts ─────────────────────────────────────────────────────
    views_count = article.views.count()
    likes_count = article.likes.count()
    comments_count = article.comments.filter(is_approved=True, parent__isnull=True).count()

    # Has current visitor already liked?
    user_liked = False
    if request.user.is_authenticated:
        user_liked = ArticleLike.objects.filter(article=article, user=request.user).exists()
    else:
        user_liked = ArticleLike.objects.filter(article=article, session_key=session_key).exists()

    # ── Approved top-level comments with their approved replies ───────────────
    top_comments = (
        article.comments
        .filter(is_approved=True, parent__isnull=True)
        .prefetch_related(
            "replies__user",
        )
        .select_related("user")
        .order_by("created_at")
    )

    comment_form = CommentForm()

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
        "views_count": views_count,
        "likes_count": likes_count,
        "comments_count": comments_count,
        "user_liked": user_liked,
        "top_comments": top_comments,
        "comment_form": comment_form,
    })


@require_POST
def article_like(request, pk):
    article = get_object_or_404(Article, pk=pk, is_published=True)
    session_key = _ensure_session_key(request)
    ip = _get_client_ip(request)
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if request.user.is_authenticated:
        like_qs = ArticleLike.objects.filter(article=article, user=request.user)
        if like_qs.exists():
            like_qs.delete()
            liked = False
        else:
            ArticleLike.objects.create(
                article=article, user=request.user,
                session_key=session_key, ip_address=ip,
            )
            liked = True
    else:
        like_qs = ArticleLike.objects.filter(article=article, session_key=session_key)
        if like_qs.exists():
            like_qs.delete()
            liked = False
        else:
            ArticleLike.objects.create(
                article=article, session_key=session_key, ip_address=ip,
            )
            liked = True

    count = article.likes.count()

    if is_ajax:
        return JsonResponse({"liked": liked, "count": count})

    return redirect("articles:detail", slug=article.slug)


@require_POST
def article_comment(request, slug):
    article = get_object_or_404(Article, slug=slug, is_published=True)
    form = CommentForm(request.POST)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.article = article
        comment.parent = None
        if request.user.is_authenticated:
            comment.user = request.user
            comment.name = request.user.full_name or request.user.phone
            comment.email = request.user.email or ""
        comment.is_approved = False
        comment.save()
        messages.success(request, "Thank you. Your comment is waiting for approval.")
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)

    return redirect("articles:detail", slug=slug)


# ── Dashboard views ────────────────────────────────────────────────────────────

@role_required(User.Role.ADMIN, User.Role.DENTIST)
def dashboard_article_list(request):
    qs = (
        Article.objects
        .select_related("category", "author")
        .annotate(
            views_count=Count("views", distinct=True),
            likes_count=Count("likes", distinct=True),
            approved_comments=Count(
                "comments",
                filter=Q(comments__is_approved=True, comments__parent__isnull=True),
                distinct=True,
            ),
            pending_comments=Count(
                "comments",
                filter=Q(comments__is_approved=False, comments__parent__isnull=True),
                distinct=True,
            ),
        )
        .order_by("-created_at")
    )

    is_dentist = request.user.role == User.Role.DENTIST
    can_manage_all = request.user.role == User.Role.ADMIN or request.user.is_superuser

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

    return render(request, "dashboard/articles/list.html", {
        "articles": page,
        "page_obj": page,
        "q": q,
        "status_filter": status_filter,
        "category_filter": category_filter,
        "categories": categories,
        "total": paginator.count,
        "is_dentist": is_dentist,
        "can_manage_all": can_manage_all,
    })


@role_required(User.Role.ADMIN)
def dashboard_category_list(request):
    categories = (
        ArticleCategory.objects
        .annotate(article_count=Count("articles", distinct=True))
        .order_by("name")
    )
    form = ArticleCategoryForm()

    if request.method == "POST":
        form = ArticleCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Article category created successfully.")
            return redirect("articles:dashboard_categories")

    return render(
        request,
        "dashboard/articles/categories.html",
        {"categories": categories, "form": form},
    )


@role_required(User.Role.ADMIN)
def dashboard_category_edit(request, pk):
    category = get_object_or_404(ArticleCategory, pk=pk)
    if request.method == "POST":
        form = ArticleCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Article category updated successfully.")
            return redirect("articles:dashboard_categories")
    else:
        form = ArticleCategoryForm(instance=category)
    return render(
        request,
        "dashboard/articles/category_form.html",
        {"form": form, "category": category},
    )


@role_required(User.Role.ADMIN)
@require_POST
def dashboard_category_delete(request, pk):
    category = get_object_or_404(ArticleCategory, pk=pk)
    title = category.name
    category.delete()
    messages.success(request, f'Article category "{title}" deleted.')
    return redirect("articles:dashboard_categories")


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
    return render(request, "dashboard/articles/preview.html", {"article": article})


@role_required(User.Role.ADMIN, User.Role.DENTIST)
def dashboard_article_image_upload(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    upload = request.FILES.get("file")
    if not upload:
        return JsonResponse({"error": "No file provided"}, status=400)

    try:
        validate_uploaded_image(upload)
    except ValidationError as exc:
        return JsonResponse({"error": " ".join(exc.messages)}, status=400)

    filename = get_valid_filename(os.path.basename(upload.name))
    path = default_storage.save(f"articles/uploads/{uuid.uuid4().hex}-{filename}", upload)
    url = request.build_absolute_uri(f"{settings.MEDIA_URL}{path}")
    return JsonResponse({"location": url})


# ── Dashboard comment management ───────────────────────────────────────────────

@role_required(User.Role.ADMIN, User.Role.DENTIST)
def dashboard_comment_list(request):
    qs = (
        ArticleComment.objects
        .filter(parent__isnull=True)
        .select_related("article", "article__author", "user")
        .prefetch_related("replies__user")
        .order_by("-created_at")
    )

    is_dentist = request.user.role == User.Role.DENTIST
    if is_dentist:
        qs = qs.filter(article__author=request.user)

    status = request.GET.get("status", "pending")
    article_filter = request.GET.get("article", "")

    if status == "pending":
        qs = qs.filter(is_approved=False)
    elif status == "approved":
        qs = qs.filter(is_approved=True)
    # "all" shows everything

    if article_filter:
        qs = qs.filter(article__pk=article_filter)

    # Articles dropdown for filter
    article_qs = Article.objects.all()
    if is_dentist:
        article_qs = article_qs.filter(author=request.user)

    pending_count = qs.model.objects.filter(parent__isnull=True, is_approved=False)
    if is_dentist:
        pending_count = pending_count.filter(article__author=request.user)
    pending_count = pending_count.count()

    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get("page"))

    return render(request, "dashboard/articles/comments.html", {
        "comments": page,
        "page_obj": page,
        "status": status,
        "article_filter": article_filter,
        "article_list": article_qs,
        "pending_count": pending_count,
        "is_dentist": is_dentist,
        "reply_form": ReplyForm(),
    })


@role_required(User.Role.ADMIN, User.Role.DENTIST)
@require_POST
def dashboard_comment_approve(request, pk):
    comment = get_object_or_404(ArticleComment, pk=pk)

    if request.user.role == User.Role.DENTIST and comment.article.author != request.user:
        messages.error(request, "Permission denied.")
        return redirect("articles:dashboard_comments")

    comment.is_approved = not comment.is_approved
    comment.save()
    state = "approved" if comment.is_approved else "hidden"
    messages.success(request, f'Comment {state}.')
    return redirect(request.META.get("HTTP_REFERER", "articles:dashboard_comments"))


@role_required(User.Role.ADMIN, User.Role.DENTIST)
@require_POST
def dashboard_comment_reply(request, pk):
    parent = get_object_or_404(ArticleComment, pk=pk, parent__isnull=True)

    if request.user.role == User.Role.DENTIST and parent.article.author != request.user:
        messages.error(request, "Permission denied.")
        return redirect("articles:dashboard_comments")

    form = ReplyForm(request.POST)
    if form.is_valid():
        ArticleComment.objects.create(
            article=parent.article,
            parent=parent,
            user=request.user,
            name=request.user.full_name or request.user.phone,
            email=request.user.email or "",
            comment=form.cleaned_data["reply"],
            is_approved=True,
        )
        messages.success(request, "Reply posted.")
    else:
        messages.error(request, "Reply cannot be empty.")

    return redirect(request.META.get("HTTP_REFERER", "articles:dashboard_comments"))


@role_required(User.Role.ADMIN, User.Role.DENTIST)
@require_POST
def dashboard_comment_delete(request, pk):
    comment = get_object_or_404(ArticleComment, pk=pk)

    if request.user.role == User.Role.DENTIST and comment.article.author != request.user:
        messages.error(request, "Permission denied.")
        return redirect("articles:dashboard_comments")

    comment.delete()
    messages.success(request, "Comment deleted.")
    return redirect(request.META.get("HTTP_REFERER", "articles:dashboard_comments"))
