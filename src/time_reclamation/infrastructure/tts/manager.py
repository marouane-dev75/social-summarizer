"""
TTS Manager Module

This module provides a high-level interface for generating speech
through various TTS providers with automatic provider selection and fallback.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from .interface import TTSProvider, TTSResult, TTSStatus
from .providers.kokoro import KokoroProvider
from src.time_reclamation.config import get_config_manager
from src.time_reclamation.infrastructure import get_logger


class TTSManager:
    """
    High-level TTS manager that handles multiple providers.
    
    This class provides a simple interface for generating speech
    and automatically handles provider selection, configuration, and resource management.
    """
    
    def __init__(self):
        """Initialize the TTS manager."""
        self.logger = get_logger()
        self._providers: Dict[str, TTSProvider] = {}  # keyed by instance name
        self._provider_instances: Dict[str, Dict[str, Any]] = {}  # metadata about instances
        self._initialize_providers()
    
    def _initialize_providers(self) -> None:
        """Initialize provider instances from configuration."""
        try:
            config_manager = get_config_manager()
            
            # Get TTS provider instances from config
            provider_instances = config_manager.get_tts_provider_instances()
            
            for instance_config in provider_instances:
                instance_name = instance_config.name
                provider_type = instance_config.type.lower()
                enabled = instance_config.enabled
                config_dict = instance_config.config
                
                if not instance_name:
                    self.logger.warning("TTS provider instance missing name, skipping")
                    continue
                
                if not enabled:
                    self.logger.debug(f"Skipping disabled TTS provider instance: {instance_name}")
                    continue
                    
                # Validate instance name uniqueness
                if instance_name in self._providers:
                    self.logger.error(f"Duplicate TTS provider instance name: {instance_name}")
                    continue
                
                # Create provider based on type
                if provider_type == "kokoro":
                    provider = KokoroProvider(instance_name, config_dict)
                else:
                    self.logger.warning(f"Unknown TTS provider type: {provider_type} for instance: {instance_name}")
                    continue
                
                # Register the provider
                self._providers[instance_name] = provider
                self._provider_instances[instance_name] = {
                    'type': provider_type,
                    'name': instance_name,
                    'configured': provider.is_configured()
                }
                
                if provider.is_configured():
                    self.logger.info(f"{provider_type.title()} provider '{instance_name}' initialized and configured")
                else:
                    self.logger.info(f"{provider_type.title()} provider '{instance_name}' initialized but not configured")
                    
        except Exception as e:
            self.logger.error(f"Failed to initialize TTS providers: {str(e)}")
    
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
    
    def get_provider_instance(self, instance_name: str) -> Optional[TTSProvider]:
        """
        Get a specific provider instance.
        
        Args:
            instance_name: Name of the provider instance to get
            
        Returns:
            Optional[TTSProvider]: Provider instance or None if not available
        """
        return self._providers.get(instance_name)
    
    def _generate_filename(self, user_filename: Optional[str] = None) -> str:
        """
        Generate an output filename.
        
        Args:
            user_filename: User-provided filename (optional)
            
        Returns:
            str: Generated or validated filename
        """
        if user_filename:
            # Ensure it has .wav extension
            if not user_filename.lower().endswith('.wav'):
                user_filename += '.wav'
            return user_filename
        
        # Generate timestamp-based filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"tts_{timestamp}.wav"
    
    def generate_speech(self, text: str, output_filename: Optional[str] = None,
                       instance_name: Optional[str] = None) -> TTSResult:
        """
        Generate speech from text using a TTS provider.
        
        Args:
            text: The text to convert to speech
            output_filename: Name of the output file (optional, will auto-generate if not provided)
            instance_name: Specific provider instance to use (optional, will auto-select if not provided)
            
        Returns:
            TTSResult: Result of the generation attempt
        """
        if not text.strip():
            return TTSResult(
                status=TTSStatus.FAILED,
                error_details="Text cannot be empty"
            )
        
        # If no instance specified, use the first available one
        if instance_name is None:
            available_instances = self.get_available_instances()
            if not available_instances:
                return TTSResult(
                    status=TTSStatus.FAILED,
                    error_details="No TTS provider instances are configured"
                )
            instance_name = available_instances[0]
            self.logger.debug(f"Auto-selected TTS provider instance: {instance_name}")
        
        # Get the provider instance
        provider = self.get_provider_instance(instance_name)
        if provider is None:
            return TTSResult(
                status=TTSStatus.FAILED,
                error_details=f"TTS provider instance '{instance_name}' is not available"
            )
        
        if not provider.is_configured():
            return TTSResult(
                status=TTSStatus.FAILED,
                error_details=f"TTS provider instance '{instance_name}' is not properly configured"
            )
        
        # Generate filename
        filename = self._generate_filename(output_filename)
        
        # Generate the speech
        self.logger.info(f"Generating speech via {provider.provider_name}")
        result = provider.generate_speech(text, filename)
        
        if result.status == TTSStatus.SUCCESS:
            self.logger.info(f"Speech generated successfully via {provider.provider_name}")
        else:
            self.logger.error(f"Failed to generate speech via {provider.provider_name}: {result.error_details}")
        
        return result
    
    def test_providers(self, instance_name: Optional[str] = None) -> Dict[str, TTSResult]:
        """
        Test TTS provider instances.
        
        Args:
            instance_name: Specific instance to test (optional, tests all if not provided)
        
        Returns:
            Dict[str, TTSResult]: Test results for each instance
        """
        results = {}
        
        instances_to_test = [instance_name] if instance_name else list(self._providers.keys())
        
        for name in instances_to_test:
            if name not in self._providers:
                results[name] = TTSResult(
                    status=TTSStatus.FAILED,
                    error_details=f"TTS provider instance '{name}' not found"
                )
                continue
                
            provider = self._providers[name]
            self.logger.info(f"Testing {provider.provider_name} provider...")
            
            if not provider.is_configured():
                results[name] = TTSResult(
                    status=TTSStatus.FAILED,
                    error_details=f"{provider.provider_name} provider is not configured"
                )
            else:
                results[name] = provider.test_connection()
        
        return results
    
    def is_any_provider_configured(self) -> bool:
        """
        Check if any TTS provider instance is configured.
        
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
    
    def cleanup_all(self) -> None:
        """
        Clean up all provider resources.
        """
        for provider in self._providers.values():
            try:
                provider.cleanup()
            except Exception as e:
                self.logger.error(f"Error cleaning up provider {provider.provider_name}: {str(e)}")
        
        self.logger.info("All TTS provider resources cleaned up")


# Global TTS manager instance
_tts_manager: Optional[TTSManager] = None


def get_tts_manager() -> TTSManager:
    """
    Get the global TTS manager instance.
    
    Returns:
        TTSManager: Global TTS manager instance
    """
    global _tts_manager
    if _tts_manager is None:
        _tts_manager = TTSManager()
    return _tts_manager


def generate_speech(text: str, output_filename: Optional[str] = None,
                   instance_name: Optional[str] = None) -> TTSResult:
    """
    Convenience function to generate speech.
    
    Args:
        text: The text to convert to speech
        output_filename: Name of the output file (optional)
        instance_name: Specific provider instance to use (optional)
        
    Returns:
        TTSResult: Result of the generation attempt
    """
    return get_tts_manager().generate_speech(text, output_filename, instance_name)