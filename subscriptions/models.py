"""
subscriptions/models.py
Dooars Granthika — Subscription module.

Models
------
Plan          — Created/managed by superuser only. Defines a subscription tier.
Subscription  — One per Library; tracks current plan, dates, and status.
Payment       — Immutable payment record for each checkout attempt.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from accounts.models import Library


# ─────────────────────────────────────────────────────────────────────────────
# Plan  (superuser-managed)
# ─────────────────────────────────────────────────────────────────────────────

class Plan(models.Model):
    """
    A subscription plan, visible to all tenants.
    Only superusers / superadmins may create, edit, or delete plans.
    Enforce this at the view/admin layer (is_superuser check).
    """

    BILLING_MONTHLY = "monthly"
    BILLING_YEARLY  = "yearly"
    BILLING_CHOICES = [
        (BILLING_MONTHLY, "Monthly"),
        (BILLING_YEARLY,  "Yearly"),
    ]

    # Slugs used in code — change with caution.
    TIER_FREE       = "free"
    TIER_BASIC      = "basic"
    TIER_SILVER     = "silver"
    TIER_GOLD       = "gold"
    TIER_PRO        = "pro"
    TIER_ENTERPRISE = "enterprise"

    TIER_CHOICES = [
        (TIER_FREE,       "Free"),
        (TIER_BASIC,      "Basic"),
        (TIER_SILVER,     "Silver"),
        (TIER_GOLD,       "Gold"),
        (TIER_PRO,        "Pro"),
        (TIER_ENTERPRISE, "Enterprise"),
    ]

    # Numeric rank — higher = higher tier.  Never reorder or reuse values.
    # Free = 0 (lowest); used for post-expiry fallback only.
    TIER_RANK: dict = {
        "free":       0,
        "basic":      1,
        "silver":     2,
        "gold":       3,
        "pro":        4,
        "enterprise": 5,
    }

    # ── Identity ──────────────────────────────────────────────────────────
    name        = models.CharField(max_length=80, unique=True)
    slug        = models.SlugField(max_length=80, unique=True)
    tier        = models.CharField(max_length=20, choices=TIER_CHOICES, default=TIER_BASIC, db_index=True)
    tagline     = models.CharField(max_length=160, blank=True, help_text="One-line plan pitch shown on the Plans page.")
    description = models.TextField(blank=True)

    # ── Pricing ───────────────────────────────────────────────────────────
    price         = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(0)])
    billing_cycle = models.CharField(max_length=10, choices=BILLING_CHOICES, default=BILLING_MONTHLY)
    duration_days = models.PositiveIntegerField(default=30, help_text="Subscription validity in days (30 = monthly, 365 = yearly).")
    is_free       = models.BooleanField(default=False, help_text="Free plan — no payment required; used as post-expiry fallback.")

    # ── Feature limits ────────────────────────────────────────────────────
    max_members    = models.PositiveIntegerField(default=50,   help_text="Max member registrations allowed.")
    max_books      = models.PositiveIntegerField(default=500,  help_text="Max bibliographic Book records allowed.")
    max_staff      = models.PositiveIntegerField(default=2,    help_text="Max staff (non-superuser) accounts allowed.")
    max_book_copies = models.PositiveIntegerField(default=1000, help_text="Max total BookCopy records allowed.")

    # ── Feature toggles ───────────────────────────────────────────────────
    allow_reports          = models.BooleanField(default=True)
    allow_export           = models.BooleanField(default=False)
    allow_sms              = models.BooleanField(default=False)
    allow_email_reminders  = models.BooleanField(default=True)
    allow_api_access       = models.BooleanField(default=False)
    allow_custom_branding  = models.BooleanField(default=False)
    allow_advance_booking  = models.BooleanField(default=False)
    priority_support       = models.BooleanField(default=False)

    # ── Display ───────────────────────────────────────────────────────────
    is_popular    = models.BooleanField(default=False, help_text="Highlight this plan as 'Most Popular'.")
    is_active     = models.BooleanField(default=True,  help_text="Inactive plans are hidden from the Plans page.")
    display_order = models.PositiveIntegerField(default=0, help_text="Lower = shown first.")

    # ── Audit ─────────────────────────────────────────────────────────────
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_plans",
        limit_choices_to={"is_superuser": True},
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ["display_order", "price"]
        verbose_name        = "Plan"
        verbose_name_plural = "Plans"

    def __str__(self):
        label = "Free" if self.is_free else f"₹{self.price}/{self.get_billing_cycle_display()}"
        return f"{self.name} ({label})"

    @property
    def price_display(self) -> str:
        return "Free" if self.is_free else f"₹{self.price:,.0f}"

    @property
    def tier_rank(self) -> int:
        """Integer rank for upgrade comparison. Higher = higher tier."""
        return self.TIER_RANK.get(self.tier, 0)

    def is_upgrade_from(self, other: "Plan") -> bool:
        """Return True if self is strictly higher tier than other."""
        return self.tier_rank > other.tier_rank

    @property
    def feature_list(self) -> list[str]:
        """Convenience: returns human-readable feature strings for templates."""
        items = [
            f"Up to {self.max_members} members",
            f"Up to {self.max_books} book titles",
            f"Up to {self.max_book_copies} physical copies",
            f"Up to {self.max_staff} staff accounts",
        ]
        toggles = {
            "Reports & Analytics":   self.allow_reports,
            "Data Export (CSV/PDF)": self.allow_export,
            "SMS Reminders":         self.allow_sms,
            "Email Reminders":       self.allow_email_reminders,
            "API Access":            self.allow_api_access,
            "Custom Branding":       self.allow_custom_branding,
            "Advance Booking":       self.allow_advance_booking,
            "Priority Support":      self.priority_support,
        }
        for label, enabled in toggles.items():
            if enabled:
                items.append(label)
        return items


# ─────────────────────────────────────────────────────────────────────────────
# Subscription  (one per Library)
# ─────────────────────────────────────────────────────────────────────────────

class Subscription(models.Model):
    """
    Active subscription record for a Library.
    Replaces the inline Subscription model in accounts/models.py.
    """

    STATUS_ACTIVE    = "active"
    STATUS_EXPIRED   = "expired"
    STATUS_CANCELLED = "cancelled"
    STATUS_TRIAL     = "trial"

    STATUS_CHOICES = [
        (STATUS_ACTIVE,    "Active"),
        (STATUS_EXPIRED,   "Expired"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_TRIAL,     "Trial"),
    ]

    library     = models.OneToOneField(Library, on_delete=models.CASCADE, related_name="subscription_detail")
    plan        = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE, db_index=True)

    start_date  = models.DateField(default=date.today)
    expiry_date = models.DateField()

    # ── Trial tracking ────────────────────────────────────────────────────
    trial_used    = models.BooleanField(default=False, help_text="True once a trial has been started; never resets.")
    trial_ends_at = models.DateField(null=True, blank=True, help_text="Date the trial period ends.")

    # ── Renewal tracking ──────────────────────────────────────────────────
    auto_renew      = models.BooleanField(default=False)
    renewal_count   = models.PositiveIntegerField(default=0)
    last_renewed_at = models.DateTimeField(null=True, blank=True)

    # ── Notes ─────────────────────────────────────────────────────────────
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ["-created_at"]
        verbose_name        = "Subscription"
        verbose_name_plural = "Subscriptions"

    def __str__(self):
        return f"{self.library} → {self.plan} ({self.status})"

    # ── Computed helpers ──────────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        return self.status in (self.STATUS_ACTIVE, self.STATUS_TRIAL) and self.expiry_date >= date.today()

    @property
    def is_on_trial(self) -> bool:
        return self.status == self.STATUS_TRIAL and self.expiry_date >= date.today()

    @property
    def days_remaining(self) -> int:
        return max(0, (self.expiry_date - date.today()).days)

    @property
    def is_expiring_soon(self) -> bool:
        """True if active/trial subscription expires within 7 days."""
        return self.is_active and 0 < self.days_remaining <= 7

    # ── Lifecycle methods ─────────────────────────────────────────────────

    def activate_trial(self, plan: Plan, trial_days: int = 14) -> None:
        """
        Start a free trial on the given plan.
        May only be called once per library (trial_used guards this).
        Caller must check trial_used before calling.
        """
        self.plan          = plan
        self.status        = self.STATUS_TRIAL
        self.start_date    = date.today()
        self.expiry_date   = date.today() + timedelta(days=trial_days)
        self.trial_used    = True
        self.trial_ends_at = self.expiry_date
        self.save()

    def expire_to_free(self) -> None:
        """
        Called automatically when a paid/trial subscription expires.
        Falls back to the active Free plan (no payment, no trial).
        Does NOT go through activate() so the downgrade guard is bypassed
        intentionally — expiry-driven fallback is always allowed.
        """
        free_plan = (
            Plan.objects.filter(tier=Plan.TIER_FREE, is_free=True, is_active=True).first()
            or Plan.objects.filter(is_free=True, is_active=True).first()
        )
        if not free_plan:
            # No free plan configured — just mark expired and leave it.
            self.status = self.STATUS_EXPIRED
            self.save(update_fields=["status", "updated_at"])
            return
        self.plan        = free_plan
        self.status      = self.STATUS_ACTIVE
        self.start_date  = date.today()
        # Free plan has no expiry — set a far-future sentinel date.
        self.expiry_date = date.today() + timedelta(days=36500)  # ~100 years
        self.save(update_fields=["plan", "status", "start_date", "expiry_date", "updated_at"])

    def activate(self, plan: Plan) -> None:
        """
        User-initiated plan switch: upgrade or same-tier renewal.

        Rules:
        - Same tier → renewal (always allowed).
        - Higher tier → upgrade (always allowed).
        - Lower tier → raises ValueError (user can never downgrade).

        Note: expiry-driven fallback to free uses expire_to_free(), not this method.
        """
        if plan.tier_rank < self.plan.tier_rank:
            raise ValueError(
                f"Downgrade not allowed: cannot move from "
                f"'{self.plan.tier}' (rank {self.plan.tier_rank}) "
                f"to '{plan.tier}' (rank {plan.tier_rank})."
            )
        self.plan        = plan
        self.status      = self.STATUS_ACTIVE
        self.start_date  = date.today()
        self.expiry_date = date.today() + timedelta(days=plan.duration_days)
        self.renewal_count  += 1
        self.last_renewed_at = timezone.now()
        self.save()


# ─────────────────────────────────────────────────────────────────────────────
# Payment
# ─────────────────────────────────────────────────────────────────────────────

class Payment(models.Model):
    """
    Immutable record of each payment attempt.
    STATUS_SUCCESS → triggers Subscription.activate().
    """

    STATUS_PENDING  = "pending"
    STATUS_SUCCESS  = "success"
    STATUS_FAILED   = "failed"
    STATUS_REFUNDED = "refunded"

    STATUS_CHOICES = [
        (STATUS_PENDING,  "Pending"),
        (STATUS_SUCCESS,  "Success"),
        (STATUS_FAILED,   "Failed"),
        (STATUS_REFUNDED, "Refunded"),
    ]

    METHOD_RAZORPAY = "razorpay"
    METHOD_STRIPE   = "stripe"
    METHOD_UPI      = "upi"
    METHOD_MANUAL   = "manual"

    METHOD_CHOICES = [
        (METHOD_RAZORPAY, "Razorpay"),
        (METHOD_STRIPE,   "Stripe"),
        (METHOD_UPI,      "UPI"),
        (METHOD_MANUAL,   "Manual / Offline"),
    ]

    # ── Identity ──────────────────────────────────────────────────────────
    payment_id     = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    library        = models.ForeignKey(Library, on_delete=models.CASCADE, related_name="subscription_payments")
    plan           = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscription_payments")
    subscription   = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name="subscription_payments")

    # ── Amount & gateway ──────────────────────────────────────────────────
    amount          = models.DecimalField(max_digits=10, decimal_places=2)
    currency        = models.CharField(max_length=5, default="INR")
    payment_method  = models.CharField(max_length=20, choices=METHOD_CHOICES, default=METHOD_RAZORPAY)
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)

    # ── Gateway refs ──────────────────────────────────────────────────────
    gateway_order_id   = models.CharField(max_length=120, blank=True)
    gateway_payment_id = models.CharField(max_length=120, blank=True)
    gateway_signature  = models.CharField(max_length=255, blank=True)
    gateway_response   = models.JSONField(default=dict, blank=True)

    # ── Audit ─────────────────────────────────────────────────────────────
    initiated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments_initiated")
    paid_at      = models.DateTimeField(null=True, blank=True)
    notes        = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ["-created_at"]
        verbose_name        = "Payment"
        verbose_name_plural = "Payments"

    def __str__(self):
        return f"Payment {self.payment_id} — {self.library} ({self.status})"

    def mark_success(self) -> None:
        """Mark payment as successful and activate the subscription."""
        self.status  = self.STATUS_SUCCESS
        self.paid_at = timezone.now()
        self.save(update_fields=["status", "paid_at", "updated_at"])
        # Activate subscription
        sub, _ = Subscription.objects.get_or_create(
            library=self.library,
            defaults={"plan": self.plan, "expiry_date": date.today() + timedelta(days=self.plan.duration_days)},
        )
        sub.activate(self.plan)
        self.subscription = sub
        self.save(update_fields=["subscription"])

    def mark_failed(self, notes: str = "") -> None:
        self.status = self.STATUS_FAILED
        if notes:
            self.notes = notes
        self.save(update_fields=["status", "notes", "updated_at"])