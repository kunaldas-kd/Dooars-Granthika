from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    # ── Report pages ───────────────────────────────────────────────────────
    path("",                  views.overview,           name="overview"),
    path("transactions/",     views.transaction_report, name="transactions"),
    path("books/",            views.book_report,        name="books"),
    path("members/",          views.member_report,      name="members"),
    path("fines/",            views.fine_report,        name="fines"),
    path("overdue/",          views.overdue_report,     name="overdue"),
    path("inventory/",        views.inventory_report,   name="inventory"),

    # ── CSV Exports ────────────────────────────────────────────────────────
    path("export/transactions/", views.export_transactions, name="export_transactions"),
    path("export/books/",        views.export_books,        name="export_books"),
    path("export/members/",      views.export_members,      name="export_members"),
    path("export/fines/",        views.export_fines,        name="export_fines"),
    path("export/overdue/",      views.export_overdue,      name="export_overdue"),
    path("export/inventory/",    views.export_inventory,    name="export_inventory"),
]
