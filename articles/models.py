from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class ArticleCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    color = models.CharField(
        max_length=30,
        default="#0B7A4B",
        help_text="Hex colour used for the category badge, e.g. #0B7A4B",
    )

    class Meta:
        verbose_name = "Article Category"
        verbose_name_plural = "Article Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "category"
            slug, n = base, 2
            while ArticleCategory.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Article(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=290, unique=True, blank=True)
    category = models.ForeignKey(
        ArticleCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="articles",
    )
    excerpt = models.TextField(
        blank=True,
        max_length=400,
        help_text="Short summary shown on listing cards (max 400 chars).",
    )
    content = models.TextField(
        help_text="Full article body. HTML tags are rendered — wrap paragraphs in <p> tags."
    )
    featured_image = models.ImageField(
        upload_to="articles/images/",
        blank=True,
        null=True,
        help_text="Recommended size: 1200×630 px (16:9).",
    )
    video_url = models.URLField(
        blank=True,
        help_text="Optional YouTube / Vimeo embed URL.",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="articles",
        limit_choices_to={"is_staff": True},
    )
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Leave blank to auto-set when you first publish.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Auto-generate slug from title
        if not self.slug:
            base = slugify(self.title) or "article"
            slug, n = base, 2
            while Article.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug

        # Auto-set published_at when first published
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()

        super().save(*args, **kwargs)

    @property
    def read_time(self):
        """Rough estimate: ~200 words per minute."""
        word_count = len(self.content.split())
        minutes = max(1, round(word_count / 200))
        return minutes


class ArticleView(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="views")
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="article_views",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["article", "session_key"],
                condition=models.Q(session_key__isnull=False),
                name="unique_article_view_per_session",
            ),
            models.UniqueConstraint(
                fields=["article", "user"],
                condition=models.Q(user__isnull=False),
                name="unique_article_view_per_user",
            ),
        ]


class ArticleLike(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="likes")
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="article_likes",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["article", "session_key"],
                condition=models.Q(session_key__isnull=False),
                name="unique_article_like_per_session",
            ),
            models.UniqueConstraint(
                fields=["article", "user"],
                condition=models.Q(user__isnull=False),
                name="unique_article_like_per_user",
            ),
        ]


class ArticleComment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="comments")
    parent = models.ForeignKey(
        "self",
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name="replies",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="article_comments",
    )
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    comment = models.TextField(max_length=2000)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.name}: {self.comment[:60]}"
