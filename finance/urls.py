# finance/urls.py
# ─────────────────────────────────────────────────────────────────────────────
# All URL patterns for the finance app.
# Include in your project urls.py with:
#   path('finance/', include('finance.urls', namespace='finance')),
# ─────────────────────────────────────────────────────────────────────────────

from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [

    # ── Media — binary-served assets ─────────────────────────────────────────
    path('logo/',                views.library_logo,        name='library_logo'),

    # ── Payment flow ──────────────────────────────────────────────────────────
    path('process/',             views.process_payment,    name='process_payment'),
    path('cash/',                views.cash_payment,       name='cash_payment'),
    path('receipt/<int:payment_id>/', views.payment_receipt, name='payment_receipt'),
    path('confirm/',             views.confirm_recovery,   name='confirm_recovery'),

    # ── Legacy URL aliases (old hyphenated paths → same views, no redirect overhead) ──
    path('process-payment/',     views.process_payment,    name='process_payment_legacy'),
    path('cash-payment/',        views.cash_payment,       name='cash_payment_legacy'),
    path('confirm-recovery/',    views.confirm_recovery,   name='confirm_recovery_legacy'),
    path('payment-receipt/<int:payment_id>/', views.payment_receipt, name='payment_receipt_legacy'),

    # ── Online / Razorpay ─────────────────────────────────────────────────────
    path('order/',               views.create_online_order,  name='create_online_order'),
    path('success/',             views.payment_success,      name='payment_success'),
    path('webhook/razorpay/<int:library_id>/', views.razorpay_webhook, name='razorpay_webhook'),

    # ── Member self-service ───────────────────────────────────────────────────
    path('my-fines/',            views.member_fine_summary, name='member_fine_summary'),

    # ── Income ────────────────────────────────────────────────────────────────
    path('income/',              views.income_list,         name='income_list'),

    # ── Expenses ──────────────────────────────────────────────────────────────
    path('expenses/',            views.expense_list,        name='expense_list'),
    path('expenses/add/',        views.add_expense,         name='add_expense'),
    path('expenses/<int:expense_id>/edit/',   views.add_expense,    name='edit_expense'),
    path('expenses/<int:expense_id>/delete/', views.delete_expense, name='delete_expense'),

    # ── Reports (finance:overview is the canonical name for finance_reports) ──
    path('reports/',             views.finance_reports,     name='overview'),
    path('daily/',               views.daily_collection,    name='daily_collection'),
    path('cash-book/',           views.cash_book,           name='cash_book'),
    path('profit-loss/',         views.profit_loss,         name='profit_loss'),

    # ── Audit log ─────────────────────────────────────────────────────────────
    path('audit/',               views.audit_log,           name='audit_log'),
]