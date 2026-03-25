from django.contrib import admin
from .models import (
    Library,
    LibraryRuleSettings,
    MemberSettings,
    SecuritySettings,
    NotificationSettings,
    AppearanceSettings,
    Subscription,
)

# ==========================================================
# 🔧 INLINE SETTINGS (OneToOne linked with Library)
# ==========================================================

class LibraryRuleSettingsInline(admin.StackedInline):
    model = LibraryRuleSettings
    extra = 0
    can_delete = False


class MemberSettingsInline(admin.StackedInline):
    model = MemberSettings
    extra = 0
    can_delete = False


class SecuritySettingsInline(admin.StackedInline):
    model = SecuritySettings
    extra = 0
    can_delete = False


class NotificationSettingsInline(admin.StackedInline):
    model = NotificationSettings
    extra = 0
    can_delete = False


class AppearanceSettingsInline(admin.StackedInline):
    model = AppearanceSettings
    extra = 0
    can_delete = False


class SubscriptionInline(admin.StackedInline):
    model = Subscription
    extra = 0
    can_delete = False


# ==========================================================
# 📚 LIBRARY ADMIN
# ==========================================================

@admin.register(Library)
class LibraryAdmin(admin.ModelAdmin):

    # ==============================
    # 📋 LIST PAGE
    # ==============================
    list_display = (
        "library_code",
        "library_name",
        "institute_name",
        "institute_email",
        "district",
        "state",
        "subscription_plan",
        "created_at",
    )

    list_display_links = ("library_code", "library_name")

    search_fields = (
        "library_code",
        "library_name",
        "institute_name",
        "institute_email",
        "user__username",
        "user__email",
    )

    list_filter = (
        "institute_type",
        "state",
        "district",
        "created_at",
    )

    list_per_page = 25

    readonly_fields = (
        "library_code",
        "created_at",
        "updated_at",
        "user_info",
    )

    fieldsets = (

        ("🔐 Admin User", {
            "fields": ("user", "user_info")
        }),

        ("📚 Library Information", {
            "fields": (
                "library_code",
                "library_name",
                "institute_name",
                "institute_type",
            )
        }),

        ("📧 Contact", {
            "fields": (
                "institute_email",
                "phone_number",
            )
        }),

        ("📍 Address", {
            "fields": (
                "address",
                "district",
                "state",
                "country",
            )
        }),

        ("🕒 System", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )

    # ==========================================================
    # 🔗 INLINE SETTINGS SECTIONS
    # ==========================================================
    inlines = [
        LibraryRuleSettingsInline,
        MemberSettingsInline,
        SecuritySettingsInline,
        NotificationSettingsInline,
        AppearanceSettingsInline,
        SubscriptionInline,
    ]

    # ==========================================================
    # 👤 USER INFO DISPLAY
    # ==========================================================
    def user_info(self, obj):
        if obj.user:
            return f"Username: {obj.user.username} | Email: {obj.user.email}"
        return "-"
    user_info.short_description = "Admin Account Info"

    # ==========================================================
    # 💳 SHOW PLAN IN LIST
    # ==========================================================
    def subscription_plan(self, obj):
        if hasattr(obj, "subscription"):
            return obj.subscription.plan
        return "-"
    subscription_plan.short_description = "Plan"