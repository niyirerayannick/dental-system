from django.contrib import admin
from django.utils.html import format_html

from .models import Article, ArticleCategory, ArticleComment, ArticleLike, ArticleView


@admin.register(ArticleCategory)
class ArticleCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "color_swatch", "description")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}

    def color_swatch(self, obj):
        return format_html(
            '<span style="display:inline-block;width:18px;height:18px;border-radius:4px;'
            'background:{};border:1px solid #ccc;vertical-align:middle;"></span> {}',
            obj.color, obj.color,
        )
    color_swatch.short_description = "Color"


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "author", "is_published", "published_at", "image_thumb")
    list_filter = ("is_published", "category")
    search_fields = ("title", "category__name", "author__email")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at", "image_thumb")
    fieldsets = (
        (None, {
            "fields": ("title", "slug", "category", "author"),
        }),
        ("Content", {
            "fields": ("excerpt", "content", "featured_image", "image_thumb", "video_url"),
        }),
        ("Publishing", {
            "fields": ("is_published", "published_at"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def image_thumb(self, obj):
        if obj.featured_image:
            return format_html(
                '<img src="{}" style="max-height:80px;border-radius:6px;" />',
                obj.featured_image.url,
            )
        return "—"
    image_thumb.short_description = "Preview"


@admin.register(ArticleView)
class ArticleViewAdmin(admin.ModelAdmin):
    list_display = ("article", "user", "session_key", "ip_address", "created_at")
    list_filter = ("created_at",)
    search_fields = ("article__title", "user__email", "ip_address")
    readonly_fields = ("article", "user", "session_key", "ip_address", "created_at")


@admin.register(ArticleLike)
class ArticleLikeAdmin(admin.ModelAdmin):
    list_display = ("article", "user", "session_key", "ip_address", "created_at")
    list_filter = ("created_at",)
    search_fields = ("article__title", "user__email")
    readonly_fields = ("article", "user", "session_key", "ip_address", "created_at")


@admin.register(ArticleComment)
class ArticleCommentAdmin(admin.ModelAdmin):
    list_display = ("article", "name", "email", "is_approved", "parent", "created_at")
    list_filter = ("is_approved", "created_at")
    search_fields = ("article__title", "name", "email", "comment")
    readonly_fields = ("created_at", "updated_at")
    actions = ["approve_comments"]

    def approve_comments(self, request, queryset):
        queryset.update(is_approved=True)
    approve_comments.short_description = "Approve selected comments"
