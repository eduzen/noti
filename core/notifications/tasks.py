"""
Celery tasks for sending push notifications.
"""

import logging
from datetime import datetime

import httpx
from celery import shared_task
from django.conf import settings

from .models import PushNotification

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
    if notification.status == "sent":
        logger.info(f"Notification {notification_id} already sent")
        return {"status": "skipped", "message": "Already sent"}

    # Mark as sending
    notification.status = "sending"
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

            return {"status": "sent", "apns_id": result.get("apns_id")}
        else:
            # Handle errors
            error_reason = result.get("reason", "Unknown error")

            # Check if token is invalid
            if error_reason in ["BadDeviceToken", "Unregistered", "DeviceTokenNotForTopic"]:
                notification.mark_token_invalid()
                logger.warning(f"Invalid token for notification {notification_id}: {error_reason}")
                return {"status": "invalid_token", "reason": error_reason}
            else:
                # Retry for other errors
                notification.increment_retry()

                if notification.retry_count < notification.max_retries:
                    # Retry the task
                    raise self.retry(exc=Exception(error_reason))
                else:
                    notification.mark_as_failed(f"Max retries exceeded: {error_reason}")
                    logger.error(f"Failed to send notification {notification_id} after retries: {error_reason}")
                    return {"status": "failed", "reason": error_reason}

    except Exception as exc:
        logger.exception(f"Error sending notification {notification_id}: {exc}")

        notification.increment_retry()

        if notification.retry_count < notification.max_retries:
            # Retry the task
            raise self.retry(exc=exc)
        else:
            notification.mark_as_failed(str(exc))
            return {"status": "failed", "error": str(exc)}


def build_apns_payload(notification: PushNotification) -> dict:
    """
    Build the APNs payload from a notification.

    Args:
        notification: PushNotification instance

    Returns:
        dict: APNs payload
    """
    payload = {
        "aps": {
            "alert": {
                "title": notification.title,
                "body": notification.body,
            },
            "sound": notification.sound,
        }
    }

    # Add badge if specified
    if notification.badge is not None:
        payload["aps"]["badge"] = notification.badge

    # Add category if specified
    if notification.category:
        payload["aps"]["category"] = notification.category

    # Add thread_id if specified
    if notification.thread_id:
        payload["aps"]["thread-id"] = notification.thread_id

    # Add custom data
    if notification.data:
        payload.update(notification.data)

    return payload


def send_to_apns(device_token: str, payload: dict) -> dict:
    """
    Send notification to APNs using HTTP/2.

    This is a basic implementation using httpx. For production, you may want to
    use a library like aioapns or PyAPNs2.

    Args:
        device_token: Device token to send to
        payload: Notification payload

    Returns:
        dict: Response with success status and details
    """
    # APNs server URL
    if settings.APNS_USE_SANDBOX:
        apns_server = "https://api.sandbox.push.apple.com"
    else:
        apns_server = "https://api.push.apple.com"

    apns_url = f"{apns_server}/3/device/{device_token}"

    # TODO: Implement proper authentication
    # For production, you need to either:
    # 1. Use JWT tokens with your APNs key
    # 2. Use certificate-based authentication
    #
    # This is a placeholder that shows the structure.
    # You'll need to add your APNs credentials.

    headers = {
        "apns-topic": settings.APNS_BUNDLE_ID,
        "apns-push-type": "alert",
    }

    try:
        # For now, return a mock success
        # In production, you would make the actual HTTP/2 request:
        #
        # with httpx.Client(http2=True, cert=(cert_path, key_path)) as client:
        #     response = client.post(apns_url, json=payload, headers=headers, timeout=10.0)
        #
        # if response.status_code == 200:
        #     return {"success": True, "apns_id": response.headers.get("apns-id")}
        # else:
        #     error_data = response.json()
        #     return {"success": False, "reason": error_data.get("reason")}

        logger.warning(
            f"APNs is not configured. Would send to {device_token[:20]}... "
            f"with payload: {payload}"
        )

        # Mock response for development
        return {
            "success": True,
            "apns_id": f"mock-apns-id-{device_token[:10]}",
        }

    except Exception as exc:
        logger.error(f"Error sending to APNs: {exc}")
        return {
            "success": False,
            "reason": str(exc),
        }
