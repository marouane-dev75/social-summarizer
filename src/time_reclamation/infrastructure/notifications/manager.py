"""
Notification Manager Module

This module provides a high-level interface for sending notifications
through various providers with automatic provider selection and fallback.
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from .interface import NotificationProvider, NotificationResult, NotificationStatus
from .providers.telegram import TelegramProvider
from src.time_reclamation.config import get_config_manager
from src.time_reclamation.infrastructure import get_logger


class ProviderType(Enum):
    """Available notification provider types."""
    TELEGRAM = "telegram"
    # Future providers can be added here
    # EMAIL = "email"
    # SLACK = "slack"


class NotificationManager:
    """
    High-level notification manager that handles multiple providers.
    
    This class provides a simple interface for sending notifications
    and automatically handles provider selection, configuration, and fallbacks.
    """
    
    def __init__(self):
        """Initialize the notification manager."""
        self.logger = get_logger()
        self._providers: Dict[ProviderType, NotificationProvider] = {}
        self._initialize_providers()
    
    def _initialize_providers(self) -> None:
        """Initialize available notification providers."""
        try:
            # Initialize Telegram provider
            telegram_provider = TelegramProvider()
            self._providers[ProviderType.TELEGRAM] = telegram_provider
            
            if telegram_provider.is_configured():
                self.logger.info("Telegram provider initialized and configured")
            else:
                self.logger.info("Telegram provider initialized but not configured")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize Telegram provider: {str(e)}")
    
    def get_available_providers(self) -> List[ProviderType]:
        """
        Get list of available and configured providers.
        
        Returns:
            List[ProviderType]: List of configured providers
        """
        available = []
        for provider_type, provider in self._providers.items():
            if provider.is_configured():
                available.append(provider_type)
        return available
    
    def get_provider(self, provider_type: ProviderType) -> Optional[NotificationProvider]:
        """
        Get a specific notification provider.
        
        Args:
            provider_type: Type of provider to get
            
        Returns:
            Optional[NotificationProvider]: Provider instance or None if not available
        """
        return self._providers.get(provider_type)
    
    def send_message(self, message: str, provider_type: Optional[ProviderType] = None, **kwargs) -> NotificationResult:
        """
        Send a notification message.
        
        Args:
            message: The message text to send
            provider_type: Specific provider to use (optional, will auto-select if not provided)
            **kwargs: Provider-specific parameters
            
        Returns:
            NotificationResult: Result of the notification attempt
        """
        if not message.strip():
            return NotificationResult(
                status=NotificationStatus.FAILED,
                error_details="Message cannot be empty"
            )
        
        # If no provider specified, use the first available one
        if provider_type is None:
            available_providers = self.get_available_providers()
            if not available_providers:
                return NotificationResult(
                    status=NotificationStatus.FAILED,
                    error_details="No notification providers are configured"
                )
            provider_type = available_providers[0]
            self.logger.debug(f"Auto-selected provider: {provider_type.value}")
        
        # Get the provider
        provider = self.get_provider(provider_type)
        if provider is None:
            return NotificationResult(
                status=NotificationStatus.FAILED,
                error_details=f"Provider {provider_type.value} is not available"
            )
        
        if not provider.is_configured():
            return NotificationResult(
                status=NotificationStatus.FAILED,
                error_details=f"Provider {provider_type.value} is not properly configured"
            )
        
        # Send the message
        self.logger.info(f"Sending notification via {provider.provider_name}")
        result = provider.send_message(message, **kwargs)
        
        if result.status == NotificationStatus.SUCCESS:
            self.logger.info(f"Notification sent successfully via {provider.provider_name}")
        else:
            self.logger.error(f"Failed to send notification via {provider.provider_name}: {result.error_details}")
        
        return result
    
    def send_telegram_message(self, message: str, **kwargs) -> NotificationResult:
        """
        Send a message specifically via Telegram.
        
        Args:
            message: The message text to send
            **kwargs: Telegram-specific parameters (parse_mode, chat_id, etc.)
            
        Returns:
            NotificationResult: Result of the notification attempt
        """
        return self.send_message(message, ProviderType.TELEGRAM, **kwargs)
    
    def test_providers(self) -> Dict[str, NotificationResult]:
        """
        Test all available providers.
        
        Returns:
            Dict[str, NotificationResult]: Test results for each provider
        """
        results = {}
        
        for provider_type, provider in self._providers.items():
            self.logger.info(f"Testing {provider.provider_name} provider...")
            
            if not provider.is_configured():
                results[provider_type.value] = NotificationResult(
                    status=NotificationStatus.FAILED,
                    error_details=f"{provider.provider_name} provider is not configured"
                )
            else:
                results[provider_type.value] = provider.test_connection()
        
        return results
    
    def is_any_provider_configured(self) -> bool:
        """
        Check if any notification provider is configured.
        
        Returns:
            bool: True if at least one provider is configured
        """
        return len(self.get_available_providers()) > 0
    
    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status information for all providers.
        
        Returns:
            Dict[str, Dict[str, Any]]: Status information for each provider
        """
        status = {}
        
        for provider_type, provider in self._providers.items():
            status[provider_type.value] = {
                'name': provider.provider_name,
                'configured': provider.is_configured(),
                'available': provider_type in self.get_available_providers()
            }
        
        return status


# Global notification manager instance
_notification_manager: Optional[NotificationManager] = None


def get_notification_manager() -> NotificationManager:
    """
    Get the global notification manager instance.
    
    Returns:
        NotificationManager: Global notification manager instance
    """
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager


def send_notification(message: str, provider_type: Optional[ProviderType] = None, **kwargs) -> NotificationResult:
    """
    Convenience function to send a notification.
    
    Args:
        message: The message text to send
        provider_type: Specific provider to use (optional)
        **kwargs: Provider-specific parameters
        
    Returns:
        NotificationResult: Result of the notification attempt
    """
    return get_notification_manager().send_message(message, provider_type, **kwargs)