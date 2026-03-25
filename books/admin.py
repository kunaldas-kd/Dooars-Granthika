"""
books/admin.py
Dooars Granthika — Books module Django admin.

Registers:
  CategoryAdmin  — tag / taxonomy management
  BookAdmin      — catalogue record with inline physical copies
  BookCopyAdmin  — standalone copy browser (search by copy_id, filter by status)
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import Book, BookCopy, Category


# ─────────────────────────────────────────────────────────────
# Category
# ─────────────────────────────────────────────────────────────

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display        = ("name", "slug", "book_count")
    search_fields       = ("name",)
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="Books")
    def book_count(self, obj):
        return obj.books.count()


# ─────────────────────────────────────────────────────────────
# BookCopy inline (shown inside BookAdmin)
# ─────────────────────────────────────────────────────────────

class BookCopyInline(admin.TabularInline):
    model           = BookCopy
    extra           = 0
    fields          = ("copy_id", "copy_number", "status_badge", "borrowed_at", "returned_at", "created_at")
    readonly_fields = ("copy_id", "copy_number", "status_badge", "borrowed_at", "returned_at", "created_at")
    can_delete      = True
    show_change_link = True
    ordering        = ("copy_id",)

    @admin.display(description="Status")
    def status_badge(self, obj):
        colours = {
            BookCopy.Status.AVAILABLE: ("#22c55e", "Available"),
            BookCopy.Status.BORROWED:  ("#f97316", "Borrowed"),
            BookCopy.Status.LOST:      ("#ef4444", "Lost"),
            BookCopy.Status.DAMAGED:   ("#6b7280", "Damaged"),
        }
        colour, label = colours.get(obj.status, ("#6b7280", obj.status))
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;'
            'border-radius:99px;font-size:.75rem;font-weight:700;">{}</span>',
            colour, label,
        )


# ─────────────────────────────────────────────────────────────
# Book  (catalogue record)
# ─────────────────────────────────────────────────────────────

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = (
        "title", "author", "isbn", "category",
        "copy_count_display",
        "available_count_display",
        "stock_badge",
        "shelf_location", "created_at",
    )
    list_filter         = ("category", "language")
    search_fields       = ("title", "author", "isbn", "publisher")
    readonly_fields     = (
        "created_at", "updated_at",
        "copy_count_display", "available_count_display",
        "borrowed_count_display", "cover_preview",
    )
    list_per_page       = 25
    date_hierarchy      = "created_at"
    ordering            = ("-created_at",)
    list_select_related = ("category",)
    inlines             = [BookCopyInline]

    fieldsets = (
        ("Basic Information", {
            "fields": (
                "title", "author", "isbn", "category",
                "publisher", "publication_year", "language", "edition",
            ),
        }),
        ("Location", {
            "fields": ("shelf_location",),
        }),
        ("Stock Summary (read-only — derived from copies)", {
            "fields": (
                "copy_count_display",
                "available_count_display",
                "borrowed_count_display",
            ),
        }),
        ("Media & Description", {
            "fields": ("cover_image", "cover_preview", "description"),
        }),
        ("Timestamps", {
            "classes": ("collapse",),
            "fields":  ("created_at", "updated_at"),
        }),
    )

    # ── Display helpers ───────────────────────────────────────────────

    @admin.display(description="Total Copies")
    def copy_count_display(self, obj):
        return obj.copy_count

    @admin.display(description="Available")
    def available_count_display(self, obj):
        return obj.available_copy_count

    @admin.display(description="Borrowed")
    def borrowed_count_display(self, obj):
        return obj.borrowed_copy_count

    @admin.display(description="Stock Status")
    def stock_badge(self, obj):
        colours = {
            "out-stock": ("#ef4444", "Out of Stock"),
            "low-stock": ("#f97316", "Low Stock"),
            "available": ("#22c55e", "Available"),
        }
        colour, label = colours.get(obj.stock_status, ("#6b7280", "Unknown"))
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;'
            'border-radius:99px;font-size:.75rem;font-weight:700;">{}</span>',
            colour, label,
        )

    @admin.display(description="Cover")
    def cover_preview(self, obj):
        if obj.cover_image:
            return format_html(
                '<img src="{}" style="max-height:120px;border-radius:6px;" />',
                obj.cover_image_b64,
            )
        return "—"


# ─────────────────────────────────────────────────────────────
# BookCopy  (standalone change-list for searching/filtering)
# ─────────────────────────────────────────────────────────────

@admin.register(BookCopy)
class BookCopyAdmin(admin.ModelAdmin):
    list_display        = ("copy_id", "book_title", "copy_number", "status_badge", "borrowed_at", "returned_at", "created_at")
    list_filter         = ("status",)
    search_fields       = ("copy_id", "book__title", "book__isbn", "book__author")
    readonly_fields     = ("copy_id", "copy_number", "borrowed_at", "returned_at", "created_at", "updated_at")
    ordering            = ("-created_at",)
    list_select_related = ("book",)
    list_per_page       = 50

    fieldsets = (
        ("Copy Details", {
            "fields": ("copy_id", "book", "copy_number", "status"),
        }),
        ("Borrow History", {
            "fields": ("borrowed_at", "returned_at"),
        }),
        ("Timestamps", {
            "classes": ("collapse",),
            "fields":  ("created_at", "updated_at"),
        }),
    )

    @admin.display(description="Book Title")
    def book_title(self, obj):
        return obj.book.title

    @admin.display(description="Status")
    def status_badge(self, obj):
        colours = {
            BookCopy.Status.AVAILABLE: ("#22c55e", "Available"),
            BookCopy.Status.BORROWED:  ("#f97316", "Borrowed"),
            BookCopy.Status.LOST:      ("#ef4444", "Lost"),
            BookCopy.Status.DAMAGED:   ("#6b7280", "Damaged"),
        }
        colour, label = colours.get(obj.status, ("#6b7280", obj.status))
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;'
            'border-radius:99px;font-size:.75rem;font-weight:700;">{}</span>',
            colour, label,
        )

    # ── Admin actions ─────────────────────────────────────────────────

    @admin.action(description="Mark selected copies as Available")
    def mark_available(self, request, queryset):
        updated = queryset.update(status=BookCopy.Status.AVAILABLE)
        self.message_user(request, f"{updated} copy/copies marked as Available.")

    @admin.action(description="Mark selected copies as Lost")
    def mark_lost(self, request, queryset):
        updated = queryset.update(status=BookCopy.Status.LOST)
        self.message_user(request, f"{updated} copy/copies marked as Lost.")

    @admin.action(description="Mark selected copies as Damaged")
    def mark_damaged(self, request, queryset):
        updated = queryset.update(status=BookCopy.Status.DAMAGED)
        self.message_user(request, f"{updated} copy/copies marked as Damaged.")

    actions = [mark_available, mark_lost, mark_damaged]