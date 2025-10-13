from django.db import models
from django.utils import timezone


class Device(models.Model):
    """iOS device registration and tracking"""

    PLATFORM_CHOICES = [
        ("ios", "iOS"),
        ("android", "Android"),  # Future-proofing
    ]

    device_token = models.CharField(max_length=255, unique=True, db_index=True)
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES, default="ios")
    is_active = models.BooleanField(default=True, db_index=True)

    # Optional: Link to user if you have authentication
    # user = models.ForeignKey('auth.User', on_delete=models.CASCADE, null=True, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_notification_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "devices"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["device_token", "is_active"]),
        ]

    def __str__(self):
        return f"{self.platform} - {self.device_token[:20]}..."


class PushNotification(models.Model):
    """Individual push notification record for tracking and reliability"""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("queued", "Queued"),
        ("sending", "Sending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
        ("invalid_token", "Invalid Token"),
    ]

    PRIORITY_CHOICES = [
        (5, "Normal"),
        (10, "High"),
    ]

    # Target
    device = models.ForeignKey(
        Device, on_delete=models.CASCADE, related_name="notifications", null=True, blank=True
    )
    device_token = models.CharField(max_length=255, db_index=True)

    # APNs Payload
    title = models.CharField(max_length=255)
    body = models.TextField()
    badge = models.IntegerField(null=True, blank=True)
    sound = models.CharField(max_length=50, default="default")
    category = models.CharField(max_length=50, null=True, blank=True)
    thread_id = models.CharField(max_length=100, null=True, blank=True)

    # Custom data (JSON)
    data = models.JSONField(default=dict, blank=True)

    # Delivery settings
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=5)
    expiration = models.DateTimeField(
        null=True,
        blank=True,
        help_text="APNs will discard notification after this time if not delivered",
    )

    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    error_message = models.TextField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    scheduled_at = models.DateTimeField(default=timezone.now, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    # APNs response
    apns_id = models.CharField(max_length=255, null=True, blank=True, unique=True)

    class Meta:
        db_table = "push_notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "scheduled_at"]),
            models.Index(fields=["device_token", "created_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.device_token[:20]}... ({self.status})"

    def mark_as_sent(self, apns_id=None):
        """Mark notification as successfully sent"""
        self.status = "sent"
        self.sent_at = timezone.now()
        if apns_id:
            self.apns_id = apns_id
        self.save(update_fields=["status", "sent_at", "apns_id"])

    def mark_as_failed(self, error_message):
        """Mark notification as failed"""
        self.status = "failed"
        self.error_message = error_message
        self.save(update_fields=["status", "error_message"])

    def increment_retry(self):
        """Increment retry counter"""
        self.retry_count += 1
        self.status = "pending" if self.retry_count < self.max_retries else "failed"
        self.save(update_fields=["retry_count", "status"])

    def mark_token_invalid(self):
        """Mark token as invalid and deactivate device"""
        self.status = "invalid_token"
        self.save(update_fields=["status"])
        if self.device:
            self.device.is_active = False
            self.device.save(update_fields=["is_active"])
