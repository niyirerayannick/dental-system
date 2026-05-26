from .menu import get_dashboard_menu, get_dashboard_role_label


def dashboard_navigation(request):
    return {
        "dashboard_menu": get_dashboard_menu(request.user, request),
        "dashboard_role_label": get_dashboard_role_label(request.user),
    }
