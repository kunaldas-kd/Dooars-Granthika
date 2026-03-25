from django.urls import path
from . import views
from dashboards.views import admin_dashboard

app_name = "accounts"

urlpatterns = [
    # ── Authentication ──────────────────────────────────────────
    path("sign_in/",          views.view_signin,              name="signin"),
    path("sign_in/",          views.view_signin,              name="sign_in"),   # alias used by superuser views
    path("sign_up/",          views.register_library,         name="signup"),
    path("forget_password/",  views.view_forget_password,     name="forgetpassword"),
    path("sign_out/",         views.view_logout,              name="signout"),
    path("sign_out/",         views.view_logout,              name="sign_out"),  # alias used by superuser base template

    # ── Library portal ──────────────────────────────────────────
    path("admin_dashboard/",  admin_dashboard,                name="admin_dashboard"),
    path("settings/",         views.settings_view,            name="settings"),

    # ── First-time library setup (onboarding) ──────────────────
    path("library_setup/",    views.library_setup_view,       name="library_setup"),

    # ── AJAX: regenerate library code ─────────────────────────
    path("library_setup/regen_code/", views.regenerate_library_code, name="regen_code"),
]