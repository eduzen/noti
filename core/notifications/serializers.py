"""
DRF Serializers for notifications app.
"""

from rest_framework import serializers

from .models import Device, PushNotification


class DeviceSerializer(serializers.ModelSerializer):
    """Serializer for Device model"""

    class Meta:
        model = Device
        fields = [
            "id",
            "device_token",
            "platform",
            "is_active",
            "created_at",
            "updated_at",
            "last_notification_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "last_notification_at"]

    def validate_device_token(self, value):
        """Validate device token format"""
        if not value or len(value) < 10:
            raise serializers.ValidationError("Device token is invalid")
        return value


class PushNotificationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating push notifications"""

    class Meta:
        model = PushNotification
        fields = [
            "device_token",
            "title",
            "body",
            "badge",
            "sound",
            "category",
            "thread_id",
            "data",
            "priority",
            "expiration",
        ]

    def validate_device_token(self, value):
        """Validate device token format"""
        if not value or len(value) < 10:
            raise serializers.ValidationError("Device token is invalid")
        return value

    def validate_data(self, value):
        """Validate data is a dict"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Data must be a JSON object")
        return value


class PushNotificationSerializer(serializers.ModelSerializer):
    """Serializer for reading push notifications"""

    class Meta:
        model = PushNotification
        fields = [
            "id",
            "device",
            "device_token",
            "title",
            "body",
            "badge",
            "sound",
            "category",
            "thread_id",
            "data",
            "priority",
            "expiration",
            "status",
            "retry_count",
            "max_retries",
            "error_message",
            "created_at",
            "scheduled_at",
            "sent_at",
            "apns_id",
        ]
        read_only_fields = [
            "id",
            "device",
            "status",
            "retry_count",
            "error_message",
            "created_at",
            "sent_at",
            "apns_id",
        ]


class BulkNotificationSerializer(serializers.Serializer):
    """Serializer for bulk notification creation"""

    device_tokens = serializers.ListField(
        child=serializers.CharField(min_length=10), min_length=1, max_length=1000
    )
    title = serializers.CharField(max_length=255)
    body = serializers.CharField()
    badge = serializers.IntegerField(required=False, allow_null=True)
    sound = serializers.CharField(max_length=50, default="default")
    category = serializers.CharField(max_length=50, required=False, allow_null=True)
    thread_id = serializers.CharField(max_length=100, required=False, allow_null=True)
    data = serializers.JSONField(default=dict, required=False)
    priority = serializers.ChoiceField(choices=[5, 10], default=5)

    def validate_device_tokens(self, value):
        """Validate device tokens"""
        if len(value) > 1000:
            raise serializers.ValidationError("Cannot send to more than 1000 devices at once")
        return value

    def validate_data(self, value):
        """Validate data is a dict"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Data must be a JSON object")
        return value
