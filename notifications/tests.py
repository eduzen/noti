from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Device, PushNotification


class DeviceAPITests(APITestCase):
    """API-level tests for device registration flows."""

    def test_register_new_device(self):
        payload = {
            "device_token": "token-1234567890",
            "platform": "ios",
            "is_active": True,
        }

        response = self.client.post(reverse("device-list"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Device.objects.count(), 1)
        device = Device.objects.get()
        self.assertEqual(device.device_token, payload["device_token"])
        self.assertEqual(device.platform, Device.Platform.IOS)
        self.assertTrue(device.is_active)

    def test_re_register_updates_existing_device(self):
        device = Device.objects.create(
            device_token="token-1234567890", platform="ios", is_active=True
        )
        payload = {
            "device_token": device.device_token,
            "platform": "android",
            "is_active": False,
        }

        response = self.client.post(reverse("device-list"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Device.objects.count(), 1)
        device.refresh_from_db()
        self.assertEqual(device.platform, Device.Platform.ANDROID)
        self.assertFalse(device.is_active)


class PushNotificationAPITests(APITestCase):
    """API-level tests for push notification endpoints."""

    @patch("notifications.views.send_push_notification.delay")
    def test_create_notification_queues_task(self, mock_delay):
        payload = {
            "device_token": "token-9876543210",
            "title": "Hello",
            "body": "World",
            "badge": 1,
            "sound": "default",
            "data": {"foo": "bar"},
        }

        response = self.client.post(
            reverse("notification-list"), payload, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        notification = PushNotification.objects.get()
        self.assertEqual(notification.status, PushNotification.Status.QUEUED)
        self.assertIsNotNone(notification.device)
        mock_delay.assert_called_once_with(notification.id)

    @patch("notifications.views.send_push_notification.delay")
    def test_bulk_notifications_create_multiple_records(self, mock_delay):
        payload = {
            "device_tokens": ["bulk-token-111111", "bulk-token-222222"],
            "title": "Hello bulk",
            "body": "Bulk world",
            "sound": "default",
            "data": {"batch": True},
        }

        response = self.client.post(
            reverse("notification-bulk"), payload, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PushNotification.objects.count(), 2)
        self.assertEqual(Device.objects.count(), 2)
        self.assertEqual(mock_delay.call_count, 2)
        self.assertEqual(
            sorted(response.data["notification_ids"]),
            sorted(list(PushNotification.objects.values_list("id", flat=True))),
        )

    def test_stats_endpoint_returns_counts(self):
        device = Device.objects.create(
            device_token="device-stats-12345", platform="ios"
        )
        PushNotification.objects.create(
            device=device,
            device_token=device.device_token,
            title="Pending",
            body="Pending body",
            status=PushNotification.Status.PENDING,
        )
        PushNotification.objects.create(
            device=device,
            device_token=device.device_token,
            title="Queued",
            body="Queued body",
            status=PushNotification.Status.QUEUED,
        )
        PushNotification.objects.create(
            device=device,
            device_token=device.device_token,
            title="Sent",
            body="Sent body",
            status=PushNotification.Status.SENT,
        )

        response = self.client.get(reverse("notification-stats"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 3)
        self.assertEqual(response.data["pending"], 1)
        self.assertEqual(response.data["queued"], 1)
        self.assertEqual(response.data["sent"], 1)


class PushNotificationModelTests(TestCase):
    """Unit tests for model helper methods."""

    def setUp(self):
        self.device = Device.objects.create(
            device_token="model-token-123456", platform="ios", is_active=True
        )
        self.notification = PushNotification.objects.create(
            device=self.device,
            device_token=self.device.device_token,
            title="Test",
            body="Body",
            status=PushNotification.Status.PENDING,
        )

    def test_mark_as_sent_updates_status_and_timestamp(self):
        self.notification.mark_as_sent(apns_id="apns-123")

        self.notification.refresh_from_db()
        self.assertEqual(self.notification.status, PushNotification.Status.SENT)
        self.assertIsNotNone(self.notification.sent_at)
        self.assertEqual(self.notification.apns_id, "apns-123")

    def test_mark_token_invalid_deactivates_device(self):
        self.notification.mark_token_invalid()

        self.notification.refresh_from_db()
        self.device.refresh_from_db()
        self.assertEqual(
            self.notification.status, PushNotification.Status.INVALID_TOKEN
        )
        self.assertFalse(self.device.is_active)
