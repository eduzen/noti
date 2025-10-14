"""
Celery tasks for sending push notifications.
"""

import logging
from datetime import datetime

from celery import shared_task

from .models import PushNotification
from .services.apns import build_apns_payload, send_to_apns

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_push_notification(self, notification_id):
    """
    Send a push notification via APNs.

    Args:
        notification_id: ID of the PushNotification to send

    Returns:
        dict: Result of the operation
    """
    try:
        notification = PushNotification.objects.get(id=notification_id)
    except PushNotification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
        return {"status": "error", "message": "Notification not found"}

    # Check if already sent
    if notification.status == PushNotification.Status.SENT:
        logger.info(f"Notification {notification_id} already sent")
        return {"status": "skipped", "message": "Already sent"}

    # Mark as sending
    notification.status = PushNotification.Status.SENDING
    notification.save(update_fields=["status"])

    try:
        # Build APNs payload
        payload = build_apns_payload(notification)

        # Send to APNs
        result = send_to_apns(notification.device_token, payload)

        if result["success"]:
            notification.mark_as_sent(apns_id=result.get("apns_id"))
            logger.info(f"Successfully sent notification {notification_id}")

            # Update device last notification time
            if notification.device:
                notification.device.last_notification_at = datetime.now()
                notification.device.save(update_fields=["last_notification_at"])

            return {"status": PushNotification.Status.SENT, "apns_id": result.get("apns_id")}
        else:
            # Handle errors
            error_reason = result.get("reason", "Unknown error")

            # Check if token is invalid
            if error_reason in ["BadDeviceToken", "Unregistered", "DeviceTokenNotForTopic"]:
                notification.mark_token_invalid()
                logger.warning(f"Invalid token for notification {notification_id}: {error_reason}")
                return {"status": PushNotification.Status.INVALID_TOKEN, "reason": error_reason}
            else:
                # Retry for other errors
                notification.increment_retry()

                if notification.retry_count < notification.max_retries:
                    # Retry the task
                    raise self.retry(exc=Exception(error_reason))
                else:
                    notification.mark_as_failed(f"Max retries exceeded: {error_reason}")
                    logger.error(f"Failed to send notification {notification_id} after retries: {error_reason}")
                    return {"status": PushNotification.Status.FAILED, "reason": error_reason}

    except Exception as exc:
        logger.exception(f"Error sending notification {notification_id}: {exc}")

        notification.increment_retry()

        if notification.retry_count < notification.max_retries:
            # Retry the task
            raise self.retry(exc=exc)
        else:
            notification.mark_as_failed(str(exc))
            return {"status": PushNotification.Status.FAILED, "error": str(exc)}
