"""
DRF Views for notifications app.
"""

import logging

from django.db import models
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Device, PushNotification
from .serializers import (
    BulkNotificationSerializer,
    DeviceSerializer,
    PushNotificationCreateSerializer,
    PushNotificationSerializer,
)
from .tasks import send_push_notification

logger = logging.getLogger(__name__)


class DeviceViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet for managing device registrations.

    Endpoints:
    - POST /devices/ - Register a new device
    - GET /devices/ - List all devices
    - GET /devices/{id}/ - Get a specific device
    - PUT/PATCH /devices/{id}/ - Update a device
    """

    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    filterset_fields = ["platform", "is_active"]
    search_fields = ["device_token"]

    def perform_create(self, serializer):
        """Create or update device if it exists"""
        device_token = serializer.validated_data.get("device_token")
        try:
            device = Device.objects.get(device_token=device_token)
            # Update existing device
            for attr, value in serializer.validated_data.items():
                setattr(device, attr, value)
            device.save()
            serializer.instance = device
        except Device.DoesNotExist:
            # Create new device
            serializer.save()


class PushNotificationViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet for managing push notifications.

    Endpoints:
    - POST /notifications/ - Send a single push notification
    - POST /notifications/bulk/ - Send notifications to multiple devices
    - GET /notifications/ - List all notifications
    - GET /notifications/{id}/ - Get a specific notification
    - GET /notifications/stats/ - Get notification statistics
    """

    queryset = PushNotification.objects.all()
    filterset_fields = ["status", "device_token"]
    search_fields = ["title", "device_token"]
    ordering_fields = ["created_at", "sent_at", "status"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        """Return appropriate serializer class"""
        if self.action == "create":
            return PushNotificationCreateSerializer
        elif self.action == "bulk":
            return BulkNotificationSerializer
        return PushNotificationSerializer

    def perform_create(self, serializer):
        """Create notification and queue for sending"""
        notification = serializer.save()

        # Get or create device
        device, _ = Device.objects.get_or_create(
            device_token=notification.device_token,
            defaults={"platform": Device.Platform.IOS},
        )
        notification.device = device
        notification.status = PushNotification.Status.QUEUED
        notification.save()

        # Queue notification for sending
        send_push_notification.delay(notification.id)

        logger.info(
            f"Queued notification {notification.id} for device {device.device_token[:20]}..."
        )

    @action(detail=False, methods=["post"])
    def bulk(self, request):
        """
        Send notifications to multiple devices.

        POST /notifications/bulk/
        {
            "device_tokens": ["token1", "token2", ...],
            "title": "Hello",
            "body": "World",
            "badge": 1,
            "sound": "default",
            "data": {"key": "value"}
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        device_tokens = serializer.validated_data.pop("device_tokens")
        notification_data = serializer.validated_data

        # Create notifications for each device
        notifications = []
        for device_token in device_tokens:
            # Get or create device
            device, _ = Device.objects.get_or_create(
                device_token=device_token,
                defaults={"platform": Device.Platform.IOS},
            )

            # Create notification
            notification = PushNotification.objects.create(
                device=device,
                device_token=device_token,
                status=PushNotification.Status.QUEUED,
                **notification_data,
            )
            notifications.append(notification)

            # Queue for sending
            send_push_notification.delay(notification.id)

        logger.info(f"Queued {len(notifications)} notifications")

        return Response(
            {
                "message": f"Queued {len(notifications)} notifications",
                "notification_ids": [n.id for n in notifications],
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """
        Get notification statistics.

        GET /notifications/stats/
        """
        from django.db.models import Count

        stats = PushNotification.objects.aggregate(
            total=Count("id"),
            pending=Count(
                "id", filter=models.Q(status=PushNotification.Status.PENDING)
            ),
            queued=Count("id", filter=models.Q(status=PushNotification.Status.QUEUED)),
            sending=Count(
                "id", filter=models.Q(status=PushNotification.Status.SENDING)
            ),
            sent=Count("id", filter=models.Q(status=PushNotification.Status.SENT)),
            failed=Count("id", filter=models.Q(status=PushNotification.Status.FAILED)),
            invalid_token=Count(
                "id", filter=models.Q(status=PushNotification.Status.INVALID_TOKEN)
            ),
        )

        return Response(stats)
