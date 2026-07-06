from accounts.models import User

ARTICLE_DASHBOARD_ROLES = (
    User.Role.ADMIN,
    User.Role.DENTIST,
    User.Role.RECEPTIONIST,
)
ARTICLE_EDITOR_ROLES = (
    User.Role.ADMIN,
    User.Role.DENTIST,
)


def article_dashboard_flags(user):
    is_dentist = user.role == User.Role.DENTIST
    can_manage_all = user.role == User.Role.ADMIN or user.is_superuser
    can_edit_articles = can_manage_all or is_dentist
    is_read_only_staff = user.role == User.Role.RECEPTIONIST
    return {
        "is_dentist": is_dentist,
        "can_manage_all": can_manage_all,
        "can_edit_articles": can_edit_articles,
        "is_read_only_staff": is_read_only_staff,
    }


def user_can_edit_article(user, article):
    flags = article_dashboard_flags(user)
    if flags["can_manage_all"]:
        return True
    if flags["is_dentist"] and article.author_id == user.pk:
        return True
    return False
