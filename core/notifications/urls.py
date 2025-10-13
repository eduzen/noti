"""
URL configuration for notifications app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DeviceViewSet, PushNotificationViewSet

router = DefaultRouter()
router.register(r"devices", DeviceViewSet, basename="device")
router.register(r"notifications", PushNotificationViewSet, basename="notification")

urlpatterns = [
    path("", include(router.urls)),
]
