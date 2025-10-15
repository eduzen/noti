"""
Celery tasks for push notifications.
"""

import logging
from celery import shared_task

from .services.notification_service import NotificationService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_push_notification(self, notification_id):
    """
    Celery task to send a push notification.

    Args:
        notification_id: ID of the PushNotification to send

    Returns:
        dict: Result of the operation
    """
    try:
        result = NotificationService.send_notification(notification_id)

        # Handle retry if needed
        if result.status == "retry":
            raise self.retry(exc=Exception(result.data.get("reason")))

        return result.to_dict()

    except Exception as exc:
        logger.exception(
            f"Unexpected error in task for notification {notification_id}: {exc}"
        )
        # Let Celery handle the retry
        raise self.retry(exc=exc)


@shared_task
def cleanup_stuck_notifications():
    """
    Periodic task to clean up notifications stuck in 'sending' status.

    Marks notifications that have been in 'sending' state for more than 10 minutes
    as failed. This handles cases where workers crash or unexpected errors occur.

    Returns:
        dict: Number of notifications cleaned up
    """
    from django.utils import timezone
    from datetime import timedelta
    from .models import PushNotification

    stuck_threshold = timezone.now() - timedelta(minutes=10)
    stuck = PushNotification.objects.filter(
        status=PushNotification.Status.SENDING, updated_at__lt=stuck_threshold
    )

    count = stuck.update(
        status=PushNotification.Status.FAILED,
        error_message="Timeout: stuck in sending status",
    )

    if count:
        logger.warning(f"Cleaned up {count} stuck notifications")

    return {"cleaned_up": count}
