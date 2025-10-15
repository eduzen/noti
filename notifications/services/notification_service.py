"""
Business logic for sending push notifications.
"""

import logging
from datetime import datetime

from ..models import PushNotification
from .apns import build_apns_payload, send_to_apns

logger = logging.getLogger(__name__)


class NotificationSendResult:
    """Result object for notification sending attempts."""

    def __init__(self, status, **kwargs):
        self.status = status
        self.data = kwargs

    def to_dict(self):
        return {"status": self.status, **self.data}


class NotificationService:
    """Service for handling notification sending logic."""

    @staticmethod
    def send_notification(notification_id):
        """
        Send a push notification via APNs.

        Args:
            notification_id: ID of the PushNotification to send

        Returns:
            NotificationSendResult: Result of the send operation
        """
        notification = NotificationService._get_notification(notification_id)
        if not notification:
            return NotificationSendResult("error", message="Notification not found")

        if NotificationService._is_already_sent(notification):
            return NotificationSendResult("skipped", message="Already sent")

        NotificationService._mark_as_sending(notification)

        # Attempt to send
        payload = build_apns_payload(notification)
        result = send_to_apns(notification.device_token, payload)

        if result["success"]:
            return NotificationService._handle_success(notification, result)

        return NotificationService._handle_apns_error(notification, result)

    @staticmethod
    def _get_notification(notification_id):
        """Fetch notification by ID."""
        try:
            return PushNotification.objects.get(id=notification_id)
        except PushNotification.DoesNotExist:
            logger.error(f"Notification {notification_id} not found")
            return None

    @staticmethod
    def _is_already_sent(notification):
        """Check if notification was already sent."""
        if notification.status == PushNotification.Status.SENT:
            logger.info(f"Notification {notification.id} already sent")
            return True
        return False

    @staticmethod
    def _mark_as_sending(notification):
        """Update notification status to sending."""
        notification.status = PushNotification.Status.SENDING
        notification.save(update_fields=["status"])

    @staticmethod
    def _handle_success(notification, result):
        """Handle successful APNs send."""
        notification.mark_as_sent(apns_id=result.get("apns_id"))
        logger.info(f"Successfully sent notification {notification.id}")

        # Update device last notification timestamp
        if notification.device:
            notification.device.last_notification_at = datetime.now()
            notification.device.save(update_fields=["last_notification_at"])

        return NotificationSendResult(
            PushNotification.Status.SENT, apns_id=result.get("apns_id")
        )

    @staticmethod
    def _handle_apns_error(notification, result):
        """Handle APNs error response."""
        error_reason = result.get("reason", "Unknown error")

        # Check if token is invalid
        if NotificationService._is_invalid_token_error(error_reason):
            notification.mark_token_invalid()
            logger.warning(
                f"Invalid token for notification {notification.id}: {error_reason}"
            )
            return NotificationSendResult(
                PushNotification.Status.INVALID_TOKEN,
                reason=error_reason,
                should_retry=False,
            )

        # Mark for retry
        notification.increment_retry()

        if notification.retry_count < notification.max_retries:
            logger.info(
                f"Notification {notification.id} will retry (attempt {notification.retry_count})"
            )
            return NotificationSendResult(
                "retry",
                reason=error_reason,
                should_retry=True,
                retry_count=notification.retry_count,
            )

        # Max retries exceeded
        notification.mark_as_failed(f"Max retries exceeded: {error_reason}")
        logger.error(
            f"Failed notification {notification.id} after {notification.max_retries} retries"
        )
        return NotificationSendResult(
            PushNotification.Status.FAILED, reason=error_reason, should_retry=False
        )

    @staticmethod
    def _is_invalid_token_error(error_reason):
        """Check if error indicates invalid device token."""
        return error_reason in [
            "BadDeviceToken",
            "Unregistered",
            "DeviceTokenNotForTopic",
        ]
