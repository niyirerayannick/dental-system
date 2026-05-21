from django import template

register = template.Library()


@register.simple_tag
def get_recent_articles(count=2):
    try:
        from articles.models import Article
        return list(
            Article.objects.filter(is_published=True)
            .select_related("category", "author")
            .order_by("-published_at", "-created_at")[:count]
        )
    except Exception:
        return []
