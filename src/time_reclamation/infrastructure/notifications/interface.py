"""
Notification Interface Module

This module defines the abstract interface for notification providers,
allowing easy switching between different notification services.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class NotificationStatus(Enum):
    """Status of a notification attempt."""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"


@dataclass
class NotificationResult:
    """Result of a notification attempt."""
    status: NotificationStatus
    message: Optional[str] = None
    error_details: Optional[str] = None
    provider_response: Optional[Dict[str, Any]] = None


class NotificationProvider(ABC):
    """
    Abstract base class for notification providers.
    
    This interface defines the contract that all notification providers
    must implement, ensuring consistency across different services.
    """
    
    @abstractmethod
    def send_message(self, message: str, audio_file: Optional[str] = None, **kwargs) -> NotificationResult:
        """
        Send a text message, optionally with an audio file attachment.
        
        Args:
            message: The message text to send
            audio_file: Optional path to audio file to send after the message
            **kwargs: Provider-specific parameters
            
        Returns:
            NotificationResult: Result of the notification attempt
            
        Note:
            When audio_file is provided:
            - Text message is sent first
            - Audio file is sent as a separate message immediately after
            - If text succeeds but audio fails, still returns success
              (with warning in error_details)
        """
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """
        Check if the provider is properly configured.
        
        Returns:
            bool: True if the provider is ready to send notifications
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> NotificationResult:
        """
        Test the connection to the notification service.
        
        Returns:
            NotificationResult: Result of the connection test
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Get the name of the notification provider.
        
        Returns:
            str: Provider name (e.g., "Telegram", "Email", "Slack")
        """
        pass