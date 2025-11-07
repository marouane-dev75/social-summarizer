"""
LLM Manager Module

This module provides a high-level interface for generating responses
through various LLM providers with automatic provider selection and fallback.
"""

from typing import Optional, List, Dict, Any
from .interface import LLMProvider, LLMResult, LLMStatus
from .providers.llamacpp import LlamaCppProvider
from .providers.anthropic import AnthropicProvider
from .providers.openai import OpenAIProvider
from .providers.ollama import OllamaProvider
from src.time_reclamation.config import get_config_manager
from src.time_reclamation.infrastructure import get_logger


class LLMManager:
    """
    High-level LLM manager that handles multiple providers.
    
    This class provides a simple interface for generating LLM responses
    and automatically handles provider selection, configuration, and resource management.
    """
    
    def __init__(self):
        """Initialize the LLM manager."""
        self.logger = get_logger()
        self._providers: Dict[str, LLMProvider] = {}  # keyed by instance name
        self._provider_instances: Dict[str, Dict[str, Any]] = {}  # metadata about instances
        self._initialize_providers()
    
    def _initialize_providers(self) -> None:
        """Initialize provider instances from configuration."""
        try:
            config_manager = get_config_manager()
            
            # Get LLM provider instances from config
            provider_instances = config_manager.get_llm_provider_instances()
            
            for instance_config in provider_instances:
                instance_name = instance_config.name
                provider_type = instance_config.type.lower()
                enabled = instance_config.enabled
                config_dict = instance_config.config
                
                if not instance_name:
                    self.logger.warning("LLM provider instance missing name, skipping")
                    continue
                
                if not enabled:
                    self.logger.debug(f"Skipping disabled LLM provider instance: {instance_name}")
                    continue
                    
                # Validate instance name uniqueness
                if instance_name in self._providers:
                    self.logger.error(f"Duplicate LLM provider instance name: {instance_name}")
                    continue
                
                # Create provider based on type
                if provider_type == "llamacpp":
                    provider = LlamaCppProvider(instance_name, config_dict)
                elif provider_type == "anthropic":
                    provider = AnthropicProvider(instance_name, config_dict)
                elif provider_type == "openai":
                    provider = OpenAIProvider(instance_name, config_dict)
                elif provider_type == "ollama":
                    provider = OllamaProvider(instance_name, config_dict)
                else:
                    self.logger.warning(f"Unknown LLM provider type: {provider_type} for instance: {instance_name}")
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
            self.logger.error(f"Failed to initialize LLM providers: {str(e)}")
    
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
    
    def get_provider_instance(self, instance_name: str) -> Optional[LLMProvider]:
        """
        Get a specific provider instance.
        
        Args:
            instance_name: Name of the provider instance to get
            
        Returns:
            Optional[LLMProvider]: Provider instance or None if not available
        """
        return self._providers.get(instance_name)
    
    def generate_response(self, user_prompt: str, instance_name: Optional[str] = None, 
                         system_prompt: Optional[str] = None, **kwargs) -> LLMResult:
        """
        Generate a response using an LLM provider.
        
        Args:
            user_prompt: The user's input prompt
            instance_name: Specific provider instance to use (optional, will auto-select if not provided)
            system_prompt: System prompt to set context/behavior (optional)
            **kwargs: Provider-specific parameters
            
        Returns:
            LLMResult: Result of the generation attempt
        """
        if not user_prompt.strip():
            return LLMResult(
                status=LLMStatus.FAILED,
                error_details="User prompt cannot be empty"
            )
        
        # If no instance specified, use the first available one
        if instance_name is None:
            available_instances = self.get_available_instances()
            if not available_instances:
                return LLMResult(
                    status=LLMStatus.FAILED,
                    error_details="No LLM provider instances are configured"
                )
            instance_name = available_instances[0]
            self.logger.debug(f"Auto-selected LLM provider instance: {instance_name}")
        
        # Get the provider instance
        provider = self.get_provider_instance(instance_name)
        if provider is None:
            return LLMResult(
                status=LLMStatus.FAILED,
                error_details=f"LLM provider instance '{instance_name}' is not available"
            )
        
        if not provider.is_configured():
            return LLMResult(
                status=LLMStatus.FAILED,
                error_details=f"LLM provider instance '{instance_name}' is not properly configured"
            )
        
        # Generate the response
        self.logger.info(f"Generating response via {provider.provider_name}")
        result = provider.generate(system_prompt or "", user_prompt, **kwargs)
        
        if result.status == LLMStatus.SUCCESS:
            self.logger.info(f"Response generated successfully via {provider.provider_name}")
        else:
            self.logger.error(f"Failed to generate response via {provider.provider_name}: {result.error_details}")
        
        return result
    
    def generate_llamacpp_response(self, user_prompt: str, instance_name: Optional[str] = None, 
                                  system_prompt: Optional[str] = None, **kwargs) -> LLMResult:
        """
        Generate a response via a LlamaCpp instance.
        
        Args:
            user_prompt: The user's input prompt
            instance_name: Name of the LlamaCpp instance to use (optional, will auto-select first LlamaCpp instance)
            system_prompt: System prompt to set context/behavior (optional)
            **kwargs: LlamaCpp-specific parameters (temperature, max_tokens, etc.)
            
        Returns:
            LLMResult: Result of the generation attempt
        """
        # If no instance specified, find first available LlamaCpp instance
        if instance_name is None:
            for name, metadata in self._provider_instances.items():
                if metadata['type'] == 'llamacpp' and metadata['configured']:
                    instance_name = name
                    break
            
            if instance_name is None:
                return LLMResult(
                    status=LLMStatus.FAILED,
                    error_details="No configured LlamaCpp instances available"
                )
        
        return self.generate_response(user_prompt, instance_name, system_prompt, **kwargs)
    
    def test_providers(self, instance_name: Optional[str] = None) -> Dict[str, LLMResult]:
        """
        Test LLM provider instances.
        
        Args:
            instance_name: Specific instance to test (optional, tests all if not provided)
        
        Returns:
            Dict[str, LLMResult]: Test results for each instance
        """
        results = {}
        
        instances_to_test = [instance_name] if instance_name else list(self._providers.keys())
        
        for name in instances_to_test:
            if name not in self._providers:
                results[name] = LLMResult(
                    status=LLMStatus.FAILED,
                    error_details=f"LLM provider instance '{name}' not found"
                )
                continue
                
            provider = self._providers[name]
            self.logger.info(f"Testing {provider.provider_name} provider...")
            
            if not provider.is_configured():
                results[name] = LLMResult(
                    status=LLMStatus.FAILED,
                    error_details=f"{provider.provider_name} provider is not configured"
                )
            else:
                results[name] = provider.test_connection()
        
        return results
    
    def is_any_provider_configured(self) -> bool:
        """
        Check if any LLM provider instance is configured.
        
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
        
        self.logger.info("All LLM provider resources cleaned up")


# Global LLM manager instance
_llm_manager: Optional[LLMManager] = None


def get_llm_manager() -> LLMManager:
    """
    Get the global LLM manager instance.
    
    Returns:
        LLMManager: Global LLM manager instance
    """
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager()
    return _llm_manager


def generate_llm_response(user_prompt: str, instance_name: Optional[str] = None, 
                         system_prompt: Optional[str] = None, **kwargs) -> LLMResult:
    """
    Convenience function to generate an LLM response.
    
    Args:
        user_prompt: The user's input prompt
        instance_name: Specific provider instance to use (optional)
        system_prompt: System prompt to set context/behavior (optional)
        **kwargs: Provider-specific parameters
        
    Returns:
        LLMResult: Result of the generation attempt
    """
    return get_llm_manager().generate_response(user_prompt, instance_name, system_prompt, **kwargs)