"""subscriptions/admin.py"""

from django.contrib import admin
from .models import Payment, Plan, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display  = ("name", "tier", "price", "billing_cycle", "is_free", "is_popular", "is_active", "display_order")
    list_editable = ("is_active", "is_popular", "display_order")
    list_filter   = ("tier", "billing_cycle", "is_free", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "tagline")
    fieldsets = (
        ("Identity",  {"fields": ("name", "slug", "tier", "tagline", "description")}),
        ("Pricing",   {"fields": ("price", "billing_cycle", "duration_days", "is_free")}),
        ("Limits",    {"fields": ("max_members", "max_books", "max_book_copies", "max_staff")}),
        ("Features",  {"fields": (
            "allow_reports", "allow_export", "allow_sms",
            "allow_email_reminders", "allow_api_access",
            "allow_custom_branding", "allow_advance_booking", "priority_support",
        )}),
        ("Display",   {"fields": ("is_popular", "is_active", "display_order")}),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display  = ("library", "plan", "status", "start_date", "expiry_date", "days_remaining")
    list_filter   = ("status", "plan")
    search_fields = ("library__library_name",)
    readonly_fields = ("created_at", "updated_at", "last_renewed_at", "renewal_count")

    def days_remaining(self, obj):
        return obj.days_remaining
    days_remaining.short_description = "Days Left"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display  = ("payment_id", "library", "plan", "amount", "status", "payment_method", "paid_at")
    list_filter   = ("status", "payment_method", "plan")
    search_fields = ("library__library_name", "gateway_payment_id", "gateway_order_id")
    readonly_fields = ("payment_id", "created_at", "updated_at", "paid_at", "gateway_response")