"""
superuser/admin.py
==================
Django admin for the Dooars Granthika SaaS superuser models.
"""

from django.contrib import admin
from .models import Plan, Invoice, BillingTransaction, ActivityLog


# ─────────────────────────────────────────────
#  Plan
# ─────────────────────────────────────────────

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display  = ('name', 'slug', 'price', 'billing_cycle',
                     'live_subs', 'mrr_display', 'is_active')
    list_filter   = ('is_active', 'billing_cycle')
    search_fields = ('name', 'slug')
    list_editable = ('is_active',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Identity', {
            'fields': ('name', 'slug', 'description', 'is_active'),
        }),
        ('Pricing', {
            'fields': ('price', 'billing_cycle', 'trial_days'),
        }),
        ('Resource Limits', {
            'fields': ('max_books', 'max_members', 'storage_gb'),
        }),
        ('Features', {
            'fields': ('features_text',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Live Subs')
    def live_subs(self, obj):
        return obj.active_subscription_count

    @admin.display(description='MRR (₹)')
    def mrr_display(self, obj):
        return f'₹{obj.mrr:,.2f}'


# ─────────────────────────────────────────────
#  Invoice
# ─────────────────────────────────────────────

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display    = ('number', 'library_display', 'plan_name', 'amount',
                       'status', 'issued_date', 'due_date', 'paid_date')
    list_filter     = ('status',)
    search_fields   = ('number', 'library__library_name', 'library__library_code')
    readonly_fields = ('number', 'created_at', 'updated_at')
    raw_id_fields   = ('library', 'accounts_subscription')

    @admin.display(description='Library', ordering='library__library_name')
    def library_display(self, obj):
        return f'{obj.library.library_name} ({obj.library.library_code})'


# ─────────────────────────────────────────────
#  BillingTransaction
# ─────────────────────────────────────────────

@admin.register(BillingTransaction)
class BillingTransactionAdmin(admin.ModelAdmin):
    list_display    = ('reference', 'library_display', 'plan_name', 'type',
                       'amount', 'currency', 'status', 'gateway', 'created_at')
    list_filter     = ('status', 'type', 'gateway')
    search_fields   = ('reference', 'library__library_name',
                       'library__library_code', 'gateway_reference')
    readonly_fields = ('reference', 'created_at', 'updated_at')
    raw_id_fields   = ('library', 'accounts_subscription', 'invoice')

    @admin.display(description='Library', ordering='library__library_name')
    def library_display(self, obj):
        return f'{obj.library.library_name} ({obj.library.library_code})'


# ─────────────────────────────────────────────
#  ActivityLog
# ─────────────────────────────────────────────

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display    = ('created_at', 'model_name', 'object_id', 'action',
                       'user', 'library_display', 'notes_short')
    list_filter     = ('model_name', 'action')
    search_fields   = ('notes', 'action', 'user__username',
                       'library__library_name')
    readonly_fields = ('model_name', 'object_id', 'action', 'user',
                       'notes', 'library', 'accounts_subscription', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description='Library')
    def library_display(self, obj):
        if obj.library:
            return f'{obj.library.library_name} ({obj.library.library_code})'
        return '—'

    @admin.display(description='Notes')
    def notes_short(self, obj):
        return (obj.notes[:80] + '…') if len(obj.notes) > 80 else obj.notes
