"""
subscriptions/views.py
Dooars Granthika — Subscription views.

URL map (see urls.py):
    plans/                  → PlansView          (all tenants)
    my-subscription/        → MySubscriptionView (tenant)
    checkout/<plan_slug>/   → CheckoutView       (tenant)
    payment-status/<uuid>/  → PaymentStatusView  (tenant)

    # Superadmin only
    admin/plans/            → AdminPlanListView
    admin/plans/create/     → AdminPlanCreateView
    admin/plans/<id>/edit/  → AdminPlanEditView
    admin/plans/<id>/delete/→ AdminPlanDeleteView
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView, DeleteView, ListView, TemplateView, UpdateView,
)

from .forms import PlanForm
from .models import Payment, Plan, Subscription


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_library(request):
    """Return the Library linked to the logged-in user, or raise 404."""
    try:
        return request.user.library
    except Exception:
        raise Http404("No library associated with this account.")


# Trial length in days — change here to adjust globally.
TRIAL_DAYS = 14


def _resolve_subscription(library):
    """
    Fetch (or bootstrap) the library's subscription and apply any
    expiry transitions automatically.  Always returns a Subscription.

    Bootstrap logic (first-ever call, no Subscription row yet):
      • If the library has never had a trial → start a 14-day trial on
        the lowest-priced paid plan (Basic).
      • Fallback (no paid plan found) → activate the Free plan directly.

    Expiry logic (subscription row exists but has expired):
      • Call sub.expire_to_free() to drop to the Free plan automatically.
    """
    # ── Fetch existing subscription ───────────────────────────────────────
    try:
        sub = library.subscription_detail
    except Subscription.DoesNotExist:
        sub = None

    # ── Bootstrap: first-ever subscription for this library ───────────────
    if sub is None:
        basic_plan = (
            Plan.objects.filter(tier=Plan.TIER_BASIC, is_active=True).first()
            or Plan.objects.filter(is_free=False, is_active=True).order_by("price").first()
        )
        free_plan = (
            Plan.objects.filter(tier=Plan.TIER_FREE, is_free=True, is_active=True).first()
            or Plan.objects.filter(is_free=True, is_active=True).first()
        )

        if basic_plan:
            # First time → grant a trial on the Basic plan.
            sub = Subscription(library=library, plan=basic_plan,
                               expiry_date=date.today())  # overwritten below
            sub.save()  # need a PK before activate_trial writes fields
            sub.activate_trial(basic_plan, trial_days=TRIAL_DAYS)
        elif free_plan:
            # No paid plan configured → activate free directly.
            sub = Subscription.objects.create(
                library=library,
                plan=free_plan,
                start_date=date.today(),
                expiry_date=date.today() + timedelta(days=36500),
                status=Subscription.STATUS_ACTIVE,
                trial_used=True,  # no trial available, skip forever
            )
        else:
            return None
        return sub

    # ── Expiry check: auto-drop to free if subscription has lapsed ─────────
    if not sub.is_active:
        sub.expire_to_free()
        sub.refresh_from_db()

    return sub


# Keep old name as alias so other callers (PaymentStatusView etc.) still work.
def _get_or_create_subscription(library):
    return _resolve_subscription(library)


# ─────────────────────────────────────────────────────────────────────────────
# Superadmin mixin
# ─────────────────────────────────────────────────────────────────────────────

class SuperuserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser


# ─────────────────────────────────────────────────────────────────────────────
# Tenant-facing views
# ─────────────────────────────────────────────────────────────────────────────

class PlansView(LoginRequiredMixin, View):
    """
    GET /subscriptions/plans/
    Shows all active plans; highlights the current plan.
    """
    template_name = "subscriptions/plans.html"

    def get(self, request):
        library      = _get_library(request)
        subscription = _resolve_subscription(library)
        current_plan = subscription.plan if subscription else None
        plans        = Plan.objects.filter(is_active=True).order_by("display_order", "price")

        # Annotate each plan: can the library still select it?
        # Free plan is always shown but never user-selectable (system-only).
        # A paid plan is selectable only if tier >= current tier.
        current_rank = current_plan.tier_rank if current_plan else 0
        for plan in plans:
            plan.is_free_tier   = plan.is_free
            plan.is_selectable  = (not plan.is_free) and plan.tier_rank >= current_rank
            plan.is_current     = current_plan and plan.pk == current_plan.pk
            plan.is_downgrade   = plan.tier_rank < current_rank

        return render(request, self.template_name, {
            "plans":        plans,
            "subscription": subscription,
            "current_plan": current_plan,
            "on_trial":     subscription.is_on_trial if subscription else False,
            "trial_days":   subscription.days_remaining if (subscription and subscription.is_on_trial) else 0,
        })


class MySubscriptionView(LoginRequiredMixin, View):
    """
    GET /subscriptions/my-subscription/
    Shows the tenant's current subscription details, usage, and payment history.
    """
    template_name = "subscriptions/my_subscription.html"

    def get(self, request):
        library      = _get_library(request)
        subscription = _get_or_create_subscription(library)
        payments     = Payment.objects.filter(library=library).order_by("-created_at")[:10]

        # Usage stats (best-effort — gracefully skip missing apps)
        usage = {}
        try:
            from members.models import Member
            usage["members"] = Member.objects.filter(library=library).count()
        except Exception:
            usage["members"] = 0

        try:
            from books.models import Book, BookCopy
            usage["books"]      = Book.objects.filter(owner=library.user).count()
            usage["book_copies"] = BookCopy.objects.filter(book__owner=library.user).count()
        except Exception:
            usage["books"]      = 0
            usage["book_copies"] = 0

        return render(request, self.template_name, {
            "subscription": subscription,
            "payments":     payments,
            "usage":        usage,
            "plan":         subscription.plan if subscription else None,
            "on_trial":     subscription.is_on_trial if subscription else False,
            "trial_days":   subscription.days_remaining if (subscription and subscription.is_on_trial) else 0,
        })


class CheckoutView(LoginRequiredMixin, View):
    """
    GET  /subscriptions/checkout/<plan_slug>/  → show checkout page
    POST /subscriptions/checkout/<plan_slug>/  → initiate payment (upgrade/renewal only)
    """
    template_name = "subscriptions/checkout.html"

    def _get_plan(self, slug):
        return get_object_or_404(Plan, slug=slug, is_active=True)

    def get(self, request, plan_slug):
        library = _get_library(request)
        plan    = self._get_plan(plan_slug)
        sub     = _resolve_subscription(library)

        # Free-tier plans are managed by the system; users cannot check out to them.
        if plan.is_free:
            messages.error(request, "This plan is not available for selection.")
            return redirect("subscriptions:plans")

        current_rank = sub.plan.tier_rank if sub else 0
        is_downgrade = plan.tier_rank < current_rank

        if is_downgrade:
            messages.error(
                request,
                f"You cannot downgrade from {sub.plan.name} to {plan.name}. "
                "Please choose a plan equal to or higher than your current tier."
            )
            return redirect("subscriptions:plans")

        return render(request, self.template_name, {
            "plan":         plan,
            "subscription": sub,
            "library":      library,
            "is_renewal":   sub and plan.pk == sub.plan.pk,
            "on_trial":     sub.is_on_trial if sub else False,
        })

    def post(self, request, plan_slug):
        library = _get_library(request)
        plan    = self._get_plan(plan_slug)
        sub     = _resolve_subscription(library)

        # ── Block free-plan checkout (system-managed only) ─────────────────
        if plan.is_free:
            messages.error(request, "This plan is not available for selection.")
            return redirect("subscriptions:plans")

        # ── Hard block: never allow a user-initiated downgrade ─────────────
        current_rank = sub.plan.tier_rank if sub else 0
        if plan.tier_rank < current_rank:
            messages.error(
                request,
                f"Downgrade not allowed. You are currently on {sub.plan.name}. "
                "Please choose a plan equal to or higher than your current tier."
            )
            return redirect("subscriptions:plans")

        # ── All plans: create a pending payment and go to gateway ──────────
        # In production, integrate Razorpay / Stripe here.
        # For now we simulate a successful payment (demo mode).
        payment = Payment.objects.create(
            library=library,
            plan=plan,
            amount=plan.price,
            payment_method=Payment.METHOD_RAZORPAY,
            status=Payment.STATUS_PENDING,
            initiated_by=request.user,
            gateway_order_id=f"order_{uuid.uuid4().hex[:12].upper()}",
        )

        # --- DEMO SIMULATION: mark as success immediately ---
        # Replace this block with real gateway callback handling.
        payment.mark_success()
        # ---------------------------------------------------

        messages.success(request, f"Payment successful! You're now on the {plan.name} plan.")
        return redirect("subscriptions:payment_status", payment_id=payment.payment_id)


class PaymentStatusView(LoginRequiredMixin, View):
    """
    GET /subscriptions/payment-status/<uuid>/
    Confirms payment result for the given payment record.
    """
    template_name = "subscriptions/payment_status.html"

    def get(self, request, payment_id):
        library = _get_library(request)
        payment = get_object_or_404(Payment, payment_id=payment_id, library=library)
        return render(request, self.template_name, {
            "payment":      payment,
            "plan":         payment.plan,
            "subscription": _get_or_create_subscription(library),
        })


# ─────────────────────────────────────────────────────────────────────────────
# Superadmin plan management views
# ─────────────────────────────────────────────────────────────────────────────

class AdminPlanListView(SuperuserRequiredMixin, ListView):
    model               = Plan
    template_name       = "subscriptions/admin/plan_list.html"
    context_object_name = "plans"
    queryset            = Plan.objects.order_by("display_order", "price")


class AdminPlanCreateView(SuperuserRequiredMixin, CreateView):
    model         = Plan
    form_class    = PlanForm
    template_name = "subscriptions/admin/plan_form.html"
    success_url   = reverse_lazy("subscriptions:admin_plan_list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Plan created successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["action"] = "Create"
        return ctx


class AdminPlanEditView(SuperuserRequiredMixin, UpdateView):
    model         = Plan
    form_class    = PlanForm
    template_name = "subscriptions/admin/plan_form.html"
    success_url   = reverse_lazy("subscriptions:admin_plan_list")

    def form_valid(self, form):
        messages.success(self.request, "Plan updated successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["action"] = "Edit"
        return ctx


class AdminPlanDeleteView(SuperuserRequiredMixin, DeleteView):
    model         = Plan
    template_name = "subscriptions/admin/plan_confirm_delete.html"
    success_url   = reverse_lazy("subscriptions:admin_plan_list")

    def form_valid(self, form):
        messages.success(self.request, "Plan deleted.")
        return super().form_valid(form)


# ─────────────────────────────────────────────────────────────────────────────
# AJAX helpers
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def plan_detail_api(request, plan_slug):
    """JSON endpoint: return plan feature list for dynamic comparison."""
    plan = get_object_or_404(Plan, slug=plan_slug, is_active=True)
    return JsonResponse({
        "name":          plan.name,
        "price":         str(plan.price),
        "price_display": plan.price_display,
        "is_free":       plan.is_free,
        "tier":          plan.tier,
        "tier_rank":     plan.tier_rank,
        "duration_days": plan.duration_days,
        "features":      plan.feature_list,
    })