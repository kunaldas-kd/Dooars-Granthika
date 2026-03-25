from django.contrib import admin
from finance.models import Fine
from .models import MissingBook, Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id", "library", "member", "book",
        "issue_date", "due_date", "return_date",
        "status", "fine_amount_display", "fine_paid",
    )
    list_filter    = ("status", "fine_paid", "issue_date", "library")
    search_fields  = ("member__first_name", "member__last_name", "book__title", "pk")
    date_hierarchy = "issue_date"
    readonly_fields = (
        "created_at", "updated_at",
        "overdue_days_display", "fine_amount_display", "days_borrowed_display",
    )

    fieldsets = (
        ("Tenant", {
            "fields": ("library",),
        }),
        ("Core", {
            "fields": ("member", "book", "status"),
        }),
        ("Dates", {
            "fields": ("issue_date", "due_date", "return_date", "lost_date"),
        }),
        ("Loan Settings", {
            "fields": ("loan_duration_days", "fine_rate_per_day", "renewal_count"),
        }),
        ("Return Details", {
            "fields": ("return_condition", "damage_charge", "return_notes"),
        }),
        ("Fine", {
            "fields": (
                "fine_paid", "fine_paid_date",
                "fine_amount_display", "overdue_days_display", "days_borrowed_display",
            ),
        }),
        ("Staff", {
            "fields": ("issued_by", "returned_to"),
        }),
        ("Notes & Audit", {
            "fields": ("notes", "created_at", "updated_at"),
        }),
    )

    @admin.display(description="Fine (₹)")
    def fine_amount_display(self, obj):
        return obj.fine_amount

    @admin.display(description="Overdue Days")
    def overdue_days_display(self, obj):
        return obj.overdue_days

    @admin.display(description="Days Borrowed")
    def days_borrowed_display(self, obj):
        return obj.days_borrowed


@admin.register(MissingBook)
class MissingBookAdmin(admin.ModelAdmin):
    list_display  = (
        "id", "library", "book", "status",
        "reported_date", "penalty_amount", "penalty_paid",
    )
    list_filter   = ("status", "penalty_paid", "library")
    search_fields = (
        "book__title",
        "transaction__member__first_name",
        "transaction__member__last_name",
    )
    readonly_fields = ("created_at", "updated_at")