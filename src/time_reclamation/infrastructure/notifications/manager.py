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


# Remove ProviderType enum as we now use string-based types


class NotificationManager:
    """
    High-level notification manager that handles multiple providers.
    
    This class provides a simple interface for sending notifications
    and automatically handles provider selection, configuration, and fallbacks.
    """
    
    def __init__(self):
        """Initialize the notification manager."""
        self.logger = get_logger()
        self._providers: Dict[str, NotificationProvider] = {}  # keyed by instance name
        self._provider_instances: Dict[str, Dict[str, Any]] = {}  # metadata about instances
        self._initialize_providers()
    
    def _initialize_providers(self) -> None:
        """Initialize provider instances from configuration."""
        try:
            config_manager = get_config_manager()
            provider_instances = config_manager.get_provider_instances()
            
            for instance_config in provider_instances:
                if not instance_config.enabled:
                    self.logger.debug(f"Skipping disabled provider instance: {instance_config.name}")
                    continue
                    
                instance_name = instance_config.name
                provider_type = instance_config.type.lower()
                
                # Validate instance name uniqueness
                if instance_name in self._providers:
                    self.logger.error(f"Duplicate provider instance name: {instance_name}")
                    continue
                
                # Create provider based on type
                if provider_type == "telegram":
                    provider = TelegramProvider(instance_name, instance_config.config)
                    self._providers[instance_name] = provider
                    self._provider_instances[instance_name] = {
                        'type': provider_type,
                        'name': instance_name,
                        'configured': provider.is_configured()
                    }
                    
                    if provider.is_configured():
                        self.logger.info(f"Telegram provider '{instance_name}' initialized and configured")
                    else:
                        self.logger.info(f"Telegram provider '{instance_name}' initialized but not configured")
                else:
                    self.logger.warning(f"Unknown provider type: {provider_type} for instance: {instance_name}")
                    
        except Exception as e:
            self.logger.error(f"Failed to initialize providers: {str(e)}")
    
    def get_available_instances(self) -> List[str]:
        """
        Get list of available and configured provider instances.
        
        Returns:
            List[str]: List of configured instance names
        """
        available = []
        for instance_name, provider in self._providers.items():
            if provider.is_configured():
                available.append(instance_name)
        return available
    
    def get_provider_instance(self, instance_name: str) -> Optional[NotificationProvider]:
        """
        Get a specific provider instance.
        
        Args:
            instance_name: Name of the provider instance to get
            
        Returns:
            Optional[NotificationProvider]: Provider instance or None if not available
        """
        return self._providers.get(instance_name)
    
    def send_message(self, message: str, instance_name: Optional[str] = None, **kwargs) -> NotificationResult:
        """
        Send a notification message.
        
        Args:
            message: The message text to send
            instance_name: Specific provider instance to use (optional, will auto-select if not provided)
            **kwargs: Provider-specific parameters
            
        Returns:
            NotificationResult: Result of the notification attempt
        """
        if not message.strip():
            return NotificationResult(
                status=NotificationStatus.FAILED,
                error_details="Message cannot be empty"
            )
        
        # If no instance specified, use the first available one
        if instance_name is None:
            available_instances = self.get_available_instances()
            if not available_instances:
                return NotificationResult(
                    status=NotificationStatus.FAILED,
                    error_details="No notification provider instances are configured"
                )
            instance_name = available_instances[0]
            self.logger.debug(f"Auto-selected provider instance: {instance_name}")
        
        # Get the provider instance
        provider = self.get_provider_instance(instance_name)
        if provider is None:
            return NotificationResult(
                status=NotificationStatus.FAILED,
                error_details=f"Provider instance '{instance_name}' is not available"
            )
        
        if not provider.is_configured():
            return NotificationResult(
                status=NotificationStatus.FAILED,
                error_details=f"Provider instance '{instance_name}' is not properly configured"
            )
        
        # Send the message
        self.logger.info(f"Sending notification via {provider.provider_name}")
        result = provider.send_message(message, **kwargs)
        
        if result.status == NotificationStatus.SUCCESS:
            self.logger.info(f"Notification sent successfully via {provider.provider_name}")
        else:
            self.logger.error(f"Failed to send notification via {provider.provider_name}: {result.error_details}")
        
        return result
    
    def send_telegram_message(self, message: str, instance_name: Optional[str] = None, **kwargs) -> NotificationResult:
        """
        Send a message via a Telegram instance.
        
        Args:
            message: The message text to send
            instance_name: Name of the Telegram instance to use (optional, will auto-select first Telegram instance)
            **kwargs: Telegram-specific parameters (parse_mode, chat_id, etc.)
            
        Returns:
            NotificationResult: Result of the notification attempt
        """
        # If no instance specified, find first available Telegram instance
        if instance_name is None:
            for name, metadata in self._provider_instances.items():
                if metadata['type'] == 'telegram' and metadata['configured']:
                    instance_name = name
                    break
            
            if instance_name is None:
                return NotificationResult(
                    status=NotificationStatus.FAILED,
                    error_details="No configured Telegram instances available"
                )
        
        return self.send_message(message, instance_name, **kwargs)
    
    def test_providers(self, instance_name: Optional[str] = None) -> Dict[str, NotificationResult]:
        """
        Test provider instances.
        
        Args:
            instance_name: Specific instance to test (optional, tests all if not provided)
        
        Returns:
            Dict[str, NotificationResult]: Test results for each instance
        """
        results = {}
        
        instances_to_test = [instance_name] if instance_name else list(self._providers.keys())
        
        for name in instances_to_test:
            if name not in self._providers:
                results[name] = NotificationResult(
                    status=NotificationStatus.FAILED,
                    error_details=f"Provider instance '{name}' not found"
                )
                continue
                
            provider = self._providers[name]
            self.logger.info(f"Testing {provider.provider_name} provider...")
            
            if not provider.is_configured():
                results[name] = NotificationResult(
                    status=NotificationStatus.FAILED,
                    error_details=f"{provider.provider_name} provider is not configured"
                )
            else:
                results[name] = provider.test_connection()
        
        return results
    
    def is_any_provider_configured(self) -> bool:
        """
        Check if any notification provider instance is configured.
        
        Returns:
            bool: True if at least one provider instance is configured
        """
        return len(self.get_available_instances()) > 0
    
    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status information for all provider instances.
        
        Returns:
            Dict[str, Dict[str, Any]]: Status information for each instance
        """
        status = {}
        
        for instance_name, provider in self._providers.items():
            metadata = self._provider_instances.get(instance_name, {})
            status[instance_name] = {
                'name': provider.provider_name,
                'type': metadata.get('type', 'unknown'),
                'configured': provider.is_configured(),
                'available': instance_name in self.get_available_instances()
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


def send_notification(message: str, instance_name: Optional[str] = None, **kwargs) -> NotificationResult:
    """
    Convenience function to send a notification.
    
    Args:
        message: The message text to send
        instance_name: Specific provider instance to use (optional)
        **kwargs: Provider-specific parameters
        
    Returns:
        NotificationResult: Result of the notification attempt
    """
    return get_notification_manager().send_message(message, instance_name, **kwargs)