# finance/admin.py

from django.contrib import admin
from django.db.models import Sum
from .models import Expense, Fine, Payment, PaymentSettings


@admin.register(Fine)
class FineAdmin(admin.ModelAdmin):
    list_display  = [
        'fine_id', 'member_name', 'book_title', 'transaction_id_snapshot',
        'fine_type', 'amount', 'status', 'paid_date', 'created_at',
    ]
    list_filter   = ['status', 'fine_type', 'created_at']
    search_fields = [
        'fine_id',
        'transaction_id_snapshot',
        'member_name',
        'member_id_snapshot',
        'book_title',
        'transaction__member__first_name',
        'transaction__member__last_name',
        'transaction__book__title',
    ]
    readonly_fields = [
        'fine_id', 'transaction_id_snapshot', 'member_name', 'member_id_snapshot',
        'book_title', 'issue_date_snapshot', 'due_date_snapshot',
        'created_at', 'updated_at',
    ]
    list_select_related = ['transaction__member', 'transaction__book']

    fieldsets = (
        ("Fine Details", {
            "fields": (
                "fine_id", "library", "transaction", "fine_type",
                "amount", "status", "paid_date", "payment_method", "payment_ref",
            ),
        }),
        ("Snapshots (read-only)", {
            "classes": ("collapse",),
            "fields": (
                "transaction_id_snapshot", "member_name", "member_id_snapshot",
                "book_title", "issue_date_snapshot", "due_date_snapshot",
            ),
        }),
        ("Audit", {
            "fields": ("created_at", "updated_at"),
        }),
    )

    actions = ['mark_as_paid', 'mark_as_waived']

    def mark_as_paid(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status=Fine.STATUS_UNPAID).update(
            status=Fine.STATUS_PAID, paid_date=timezone.now().date()
        )
        self.message_user(request, f'{updated} fine(s) marked as paid.')
    mark_as_paid.short_description = 'Mark selected fines as paid'

    def mark_as_waived(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status=Fine.STATUS_UNPAID).update(
            status=Fine.STATUS_WAIVED, paid_date=timezone.now().date()
        )
        self.message_user(request, f'{updated} fine(s) waived.')
    mark_as_waived.short_description = 'Waive selected fines'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display  = [
        'pk', 'member_name_display', 'transaction_id_snapshot', 'amount',
        'method', 'status', 'receipt_number', 'collected_by', 'transaction_date',
    ]
    list_filter   = ['method', 'status', 'transaction_date']
    search_fields = [
        'fine__fine_id',
        'transaction_id_snapshot',
        'member_name',
        'member_id_snapshot',
        'receipt_number',
        'gateway_payment_id',
        'fine__transaction__member__first_name',
        'fine__transaction__member__last_name',
    ]
    readonly_fields = [
        'transaction_id_snapshot', 'member_name', 'member_id_snapshot',
        'book_title', 'fine_id_snapshot', 'fine_type_snapshot',
        'fine_amount_snapshot', 'library_name', 'created_at', 'updated_at',
    ]
    list_select_related = ['fine__transaction__member']

    def member_name_display(self, obj):
        # Prefer snapshot (always available) over FK traversal
        if obj.member_name:
            return obj.member_name
        if obj.fine and obj.fine.transaction:
            m = obj.fine.transaction.member
            return f'{m.first_name} {m.last_name}'
        return '-'
    member_name_display.short_description = 'Member'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        qs = self.get_queryset(request).filter(status=Payment.STATUS_SUCCESS)
        extra_context['total_collected'] = qs.aggregate(t=Sum('amount'))['t'] or 0
        return super().changelist_view(request, extra_context)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display  = ['date', 'description', 'category', 'amount', 'recorded_by', 'created_at']
    list_filter   = ['category', 'date']
    search_fields = ['description', 'notes', 'recorded_by']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'


@admin.register(PaymentSettings)
class PaymentSettingsAdmin(admin.ModelAdmin):
    list_display  = ['library', 'is_active', 'key_id', 'is_configured_display', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']

    def is_configured_display(self, obj):
        return obj.is_configured()
    is_configured_display.boolean     = True
    is_configured_display.short_description = 'Configured?'