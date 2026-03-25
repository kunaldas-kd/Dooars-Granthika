"""
transactions/urls.py
"""
from django.urls import path
from . import views

app_name = "transactions"

urlpatterns = [
    # ── Transaction CRUD ──────────────────────────────────────────────────────
    path("",                          views.transaction_list,   name="transaction_list"),
    path("issue/",                    views.issue_book,         name="issue_book"),
    path("<int:pk>/",                 views.transaction_detail, name="transaction_detail"),
    path("<int:pk>/return/",          views.return_book,        name="return_book"),
    path("<int:pk>/renew/",           views.renew_book,         name="renew_book"),

    # ── Overdue / Fine ────────────────────────────────────────────────────────
    path("overdue/",                  views.overdue_list,       name="overdue_list"),
    path("fines/",                    views.fine_list,          name="fine_list"),
    path("fines/pay/",                views.mark_fine_paid,     name="mark_fine_paid"),

    # ── Missing / Lost ────────────────────────────────────────────────────────
    path("missing/",                  views.missing_books,      name="missing_books"),
    path("missing/lost/",             views.mark_lost,          name="mark_lost"),
    path("missing/<int:pk>/recover/", views.mark_recovered,     name="mark_recovered"),
    path("missing/<int:pk>/penalty/", views.add_penalty,        name="add_penalty"),

    # ── AJAX / API ────────────────────────────────────────────────────────────
    path("api/member-lookup/",        views.member_lookup_api,      name="member_lookup_api"),
    path("api/member-search/",        views.member_search_api,      name="member_search_api"),
    path("api/member-suggestions/",   views.member_suggestions_api, name="member_suggestions_api"),  # ← autocomplete
    path("api/book-lookup/",          views.book_lookup_api,        name="book_lookup_api"),
    path("api/book-search/",          views.book_search_api,        name="book_search_api"),
    path("api/book-cover/<int:pk>/",  views.book_cover_image,       name="book_cover_image"),
    path("api/book-cover/copy/<str:copy_id>/", views.book_cover_by_copy_id, name="book_cover_by_copy_id"),
    path("api/member-photo/<int:pk>/", views.member_photo_image,    name="member_photo_image"),
    path("export-transactions/", views.export_transactions_excel, name="export_transactions"),
]