"""
APNs service helpers for push delivery.
"""

import logging

from django.conf import settings

from ..models import PushNotification

logger = logging.getLogger(__name__)


def build_apns_payload(notification: PushNotification) -> dict:
    """
    Build the APNs payload from a notification instance.
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

    if notification.badge is not None:
        payload["aps"]["badge"] = notification.badge

    if notification.category:
        payload["aps"]["category"] = notification.category

    if notification.thread_id:
        payload["aps"]["thread-id"] = notification.thread_id

    if notification.data:
        payload.update(notification.data)

    return payload


def send_to_apns(device_token: str, payload: dict) -> dict:
    """
    Send notification to APNs using HTTP/2.

    This is a placeholder implementation that logs the outgoing payload.
    """
    if settings.APNS_USE_SANDBOX:
        apns_server = "https://api.sandbox.push.apple.com"
    else:
        apns_server = "https://api.push.apple.com"

    apns_url = f"{apns_server}/3/device/{device_token}"

    headers = {
        "apns-topic": settings.APNS_BUNDLE_ID,
        "apns-push-type": "alert",
    }

    try:
        logger.warning(
            "APNs is not configured. Would send to %s with payload %s (headers=%s, url=%s)",
            f"{device_token[:20]}...",
            payload,
            headers,
            apns_url,
        )

        return {
            "success": True,
            "apns_id": f"mock-apns-id-{device_token[:10]}",
        }

    except Exception as exc:
        logger.error("Error sending to APNs: %s", exc)
        return {
            "success": False,
            "reason": str(exc),
        }
