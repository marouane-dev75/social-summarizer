"""Notification infrastructure package."""

from .interface import NotificationProvider, NotificationResult, NotificationStatus
from .manager import NotificationManager, get_notification_manager, send_notification

__all__ = [
    'NotificationProvider',
    'NotificationResult',
    'NotificationStatus',
    'NotificationManager',
    'get_notification_manager',
    'send_notification'
]