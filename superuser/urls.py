"""
superuser/urls.py
=================
URL patterns for the Dooars Granthika SaaS Superuser Dashboard.
Mount at:  path('superuser/', include('superuser.urls', namespace='superuser'))
"""

from django.urls import path
from . import views

app_name = 'superuser'

urlpatterns = [

    # ── Dashboard ────────────────────────────────────────────
    path('', views.dashboard, name='dashboard'),

    # ── Libraries  (accounts.Library) ────────────────────────
    path('libraries/',
         views.libraries_list,   name='libraries_list'),
    path('libraries/<int:pk>/',
         views.library_detail,   name='library_detail'),
    path('libraries/<int:pk>/activate/',
         views.library_activate, name='library_activate'),
    path('libraries/<int:pk>/suspend/',
         views.library_suspend,  name='library_suspend'),

    # ── Subscriptions  (accounts.Subscription) ───────────────
    path('subscriptions/',
         views.subscriptions_list,     name='subscriptions_list'),
    path('subscriptions/<int:pk>/',
         views.subscription_detail,    name='subscription_detail'),
    path('subscriptions/<int:pk>/activate/',
         views.activate_subscription,  name='activate_subscription'),
    path('subscriptions/<int:pk>/suspend/',
         views.suspend_subscription,   name='suspend_subscription'),
    path('subscriptions/<int:pk>/cancel/',
         views.cancel_subscription,    name='cancel_subscription'),

    # ── Plans  (superuser.Plan) ───────────────────────────────
    path('plans/',
         views.plans_list,   name='plans_list'),
    path('plans/create/',
         views.plan_create,  name='plan_create'),
    path('plans/<int:pk>/edit/',
         views.plan_edit,    name='plan_edit'),
    path('plans/<int:pk>/delete/',
         views.plan_delete,  name='plan_delete'),

    # ── Billing Transactions  (superuser.BillingTransaction) ─
    path('transactions/',
         views.transactions_list,  name='transactions_list'),
    path('transactions/<int:pk>/',
         views.transaction_detail, name='transaction_detail'),
    path('transactions/<int:pk>/retry/',
         views.transaction_retry,  name='transaction_retry'),

    # ── Invoices  (superuser.Invoice) ────────────────────────
    path('invoices/',
         views.invoices,        name='invoices'),
    path('invoices/<int:pk>/remind/',
         views.invoice_remind,  name='invoice_remind'),

    # ── Reports ──────────────────────────────────────────────
    path('reports/revenue/',
         views.revenue_report,  name='revenue_report'),
    path('reports/usage/',
         views.usage_overview,  name='usage_overview'),

    # ── Settings ─────────────────────────────────────────────
    path('settings/',
         views.settings_view,   name='settings'),
    path('settings/save/<str:section>/',
         views.settings_save,   name='settings_save'),

    # ── Staff Hierarchy ───────────────────────────────────────
    path('staff/',
         views.staff_list,       name='staff_list'),
    path('staff/add/',
         views.staff_add,        name='staff_add'),
    path('staff/<int:pk>/',
         views.staff_detail,     name='staff_detail'),
    path('staff/<int:pk>/edit/',
         views.staff_edit,       name='staff_edit'),
    path('staff/<int:pk>/deactivate/',
         views.staff_deactivate, name='staff_deactivate'),

    # ── Roles ────────────────────────────────────────────────
    path('roles/',
         views.roles_list,  name='roles_list'),
    path('roles/save/',
         views.role_save,   name='role_create'),
    path('roles/<int:pk>/save/',
         views.role_save,   name='role_edit'),
    path('roles/<int:pk>/delete/',
         views.role_delete, name='role_delete'),

    # ── Tasks ────────────────────────────────────────────────
    path('tasks/',
         views.tasks_list,          name='tasks_list'),
    path('tasks/save/',
         views.task_save,           name='task_create'),
    path('tasks/<int:pk>/save/',
         views.task_save,           name='task_edit'),
    path('tasks/<int:pk>/status/',
         views.task_status_update,  name='task_status_update'),
    path('tasks/<int:pk>/delete/',
         views.task_delete,         name='task_delete'),
]