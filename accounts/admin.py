from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, UserProfile


class UserProfileInline(admin.StackedInline):
    """Inline admin for UserProfile"""

    model = UserProfile
    can_delete = False
    verbose_name_plural = "Profile"
    fields = ["first_name", "last_name", "phone"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin for custom User model"""

    inlines = [UserProfileInline]

    list_display = ["email", "is_staff", "is_active", "is_superuser", "created_at"]
    list_filter = ["is_staff", "is_superuser", "is_active", "created_at"]
    search_fields = ["email"]
    ordering = ["-created_at"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "created_at", "updated_at")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_staff", "is_active"),
            },
        ),
    )

    readonly_fields = ["created_at", "updated_at", "last_login"]
