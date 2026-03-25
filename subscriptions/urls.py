"""subscriptions/urls.py"""

from django.urls import path
from . import views

app_name = "subscriptions"

urlpatterns = [
    # ── Tenant-facing ──────────────────────────────────────────────────────
    path("plans/",                             views.PlansView.as_view(),          name="plans"),
    path("my-subscription/",                  views.MySubscriptionView.as_view(), name="my_subscription"),
    path("checkout/<slug:plan_slug>/",         views.CheckoutView.as_view(),       name="checkout"),
    path("payment-status/<uuid:payment_id>/",  views.PaymentStatusView.as_view(),  name="payment_status"),
    path("api/plan/<slug:plan_slug>/",         views.plan_detail_api,              name="plan_api"),

    # ── Superadmin plan management ────────────────────────────────────────
    path("admin/plans/",                       views.AdminPlanListView.as_view(),   name="admin_plan_list"),
    path("admin/plans/create/",                views.AdminPlanCreateView.as_view(), name="admin_plan_create"),
    path("admin/plans/<int:pk>/edit/",         views.AdminPlanEditView.as_view(),   name="admin_plan_edit"),
    path("admin/plans/<int:pk>/delete/",       views.AdminPlanDeleteView.as_view(), name="admin_plan_delete"),
]
