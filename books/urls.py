from django.urls import path
from . import views

app_name = "books"

urlpatterns = [
    # ── CRUD ──────────────────────────────────────────────────
    path("",                  views.book_list,   name="book_list"),
    path("<int:pk>/",         views.book_detail, name="book_detail"),
    path("add/",              views.book_create, name="book_create"),
    path("<int:pk>/edit/",    views.book_update, name="book_update"),
    path("<int:pk>/delete/",  views.book_delete, name="book_delete"),

    # ── Dashboard & export ────────────────────────────────────
    path("stock/",            views.stock_dashboard,      name="stock_dashboard"),
    path("export/",           views.export_books,         name="export_books"),
    path("export/excel/",     views.export_books_excel,   name="export_books_excel"),
    path("stock/update/",     views.update_stock,         name="update_stock"),

    # ── Cover image (blob served from DB) ─────────────────────
    path("<int:pk>/cover/",   views.book_cover,           name="book_cover"),

    # ── Import ────────────────────────────────────────────────
    path("import/",           views.import_books_excel,       name="import_books_excel"),
    path("import/template/",  views.download_import_template, name="download_import_template"),

    # ── Physical copy borrow / return ─────────────────────────
    path("copies/borrow/",    views.borrow_copy,  name="borrow_copy"),
    path("copies/return/",    views.return_copy,  name="return_copy"),
]
