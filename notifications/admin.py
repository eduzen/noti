"""
Django admin configuration for notifications app.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import Device, DeviceOwner, PushNotification


@admin.register(DeviceOwner)
class DeviceOwnerAdmin(admin.ModelAdmin):
    """Admin for DeviceOwner model"""

    list_display = [
        "id",
        "external_id",
        "name",
        "email",
        "is_active",
        "device_count",
        "created_at",
    ]
    list_filter = ["is_active", "created_at"]
    search_fields = ["external_id", "name", "email"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]

    def device_count(self, obj):
        """Display count of devices owned"""
        return obj.devices.count()

    device_count.short_description = "Devices"


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    """Admin for Device model"""

    list_display = [
        "id",
        "owner",
        "platform",
        "device_token_short",
        "is_active",
        "last_notification_at",
        "created_at",
    ]
    list_filter = ["platform", "is_active", "created_at"]
    search_fields = [
        "device_token",
        "owner__external_id",
        "owner__name",
        "owner__email",
    ]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]
    autocomplete_fields = ["owner"]

    def device_token_short(self, obj):
        """Display shortened device token"""
        return (
            f"{obj.device_token[:20]}..."
            if len(obj.device_token) > 20
            else obj.device_token
        )

    device_token_short.short_description = "Device Token"


@admin.register(PushNotification)
class PushNotificationAdmin(admin.ModelAdmin):
    """Admin for PushNotification model"""

    list_display = [
        "id",
        "title",
        "device_token_short",
        "status_badge",
        "priority",
        "retry_count",
        "created_at",
        "sent_at",
    ]
    list_filter = ["status", "priority", "created_at", "sent_at"]
    search_fields = ["title", "body", "device_token"]
    readonly_fields = [
        "status",
        "retry_count",
        "error_message",
        "created_at",
        "updated_at",
        "sent_at",
        "apns_id",
    ]
    ordering = ["-created_at"]

    fieldsets = (
        (
            "Target",
            {
                "fields": ("device", "device_token"),
            },
        ),
        (
            "Notification Content",
            {
                "fields": (
                    "title",
                    "body",
                    "badge",
                    "sound",
                    "category",
                    "thread_id",
                    "data",
                ),
            },
        ),
        (
            "Delivery Settings",
            {
                "fields": ("priority", "expiration", "scheduled_at"),
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "status",
                    "retry_count",
                    "max_retries",
                    "error_message",
                    "created_at",
                    "updated_at",
                    "sent_at",
                    "apns_id",
                ),
            },
        ),
    )

    def device_token_short(self, obj):
        """Display shortened device token"""
        token = obj.device_token
        return f"{token[:20]}..." if len(token) > 20 else token

    device_token_short.short_description = "Device Token"

    def status_badge(self, obj):
        """Display status as a colored badge"""
        colors = {
            PushNotification.Status.PENDING: "#FFA500",
            PushNotification.Status.QUEUED: "#1E90FF",
            PushNotification.Status.SENDING: "#00CED1",
            PushNotification.Status.SENT: "#32CD32",
            PushNotification.Status.FAILED: "#DC143C",
            PushNotification.Status.INVALID_TOKEN: "#8B0000",
        }
        color = colors.get(obj.status, "#808080")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = "Status"
