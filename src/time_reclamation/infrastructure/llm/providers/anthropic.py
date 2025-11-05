"""
Anthropic LLM Provider

This module implements the Anthropic LLM provider using the
official anthropic Python library for Claude models.
"""

import time
from typing import Optional, Dict, Any
from ..interface import LLMProvider, LLMResult, LLMStatus
from src.time_reclamation.config import get_config_manager
from src.time_reclamation.infrastructure import get_logger


class AnthropicProvider(LLMProvider):
    """
    Anthropic LLM provider implementation.
    
    This class implements the LLMProvider interface for generating
    responses via Anthropic's Claude models using their official API.
    """
    
    def __init__(self, instance_name: str, config: Dict[str, Any]):
        """
        Initialize the Anthropic provider with instance-specific configuration.
        
        Args:
            instance_name: Name of this provider instance
            config: Configuration dictionary for this instance
        """
        self.logger = get_logger()
        self.instance_name = instance_name
        
        # Extract configuration values
        self.api_key = config.get('api_key', '')
        self.model = config.get('model', 'claude-haiku-4.5')
        self.max_tokens = config.get('max_tokens', 4000)
        self.temperature = config.get('temperature', 0.7)
        self.default_system_prompt = config.get('default_system_prompt', 
            "You are Claude, a helpful AI assistant created by Anthropic.")
        
        # Client instance (lazy loaded)
        self._client = None
        self._client_initialized = False
        
        self.logger.debug(f"Anthropic provider '{instance_name}' initialized with model: {self.model}")
    
    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return f"Anthropic ({self.instance_name})"
    
    def is_configured(self) -> bool:
        """
        Check if the provider is properly configured.
        
        Returns:
            bool: True if the provider is ready to generate responses
        """
        if not self.api_key:
            return False
            
        # Check for placeholder values
        if self.api_key in ['your-anthropic-api-key-here', 'YOUR_ANTHROPIC_API_KEY_HERE']:
            return False
            
        # Basic API key format validation (Anthropic keys start with 'sk-ant-')
        if not self.api_key.startswith('sk-ant-'):
            return False
            
        return True
    
    def _initialize_client(self) -> bool:
        """
        Initialize the Anthropic client with lazy loading.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        if self._client_initialized:
            return self._client is not None
        
        try:
            # Import anthropic
            import anthropic
        except ImportError:
            self.logger.error("anthropic library is not installed. Please install it with: pip install anthropic")
            self._client_initialized = True
            return False
        
        try:
            self.logger.debug(f"Initializing Anthropic client for model: {self.model}")
            
            # Initialize the client
            self._client = anthropic.Anthropic(api_key=self.api_key)
            
            self.logger.debug("Anthropic client initialized successfully")
            self._client_initialized = True
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing Anthropic client: {str(e)}")
            self._client_initialized = True
            return False
    
    def _format_time(self, seconds: float) -> str:
        """
        Format time duration in a human-readable format.
        
        Args:
            seconds: Time duration in seconds
            
        Returns:
            str: Formatted time string
        """
        if seconds < 1:
            return f"{seconds * 1000:.1f}ms"
        elif seconds < 60:
            return f"{seconds:.2f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            remaining_seconds = seconds % 60
            return f"{minutes}m {remaining_seconds:.1f}s"
        else:
            hours = int(seconds // 3600)
            remaining_minutes = int((seconds % 3600) // 60)
            remaining_seconds = seconds % 60
            return f"{hours}h {remaining_minutes}m {remaining_seconds:.1f}s"
    
    def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> LLMResult:
        """
        Generate a response using the Anthropic Claude model.
        
        Args:
            system_prompt: The system prompt to set context/behavior
            user_prompt: The user's input prompt
            **kwargs: Additional generation parameters
            
        Returns:
            LLMResult: Result of the generation attempt
        """
        if not self.is_configured():
            return LLMResult(
                status=LLMStatus.FAILED,
                error_details="Anthropic provider is not properly configured"
            )
        
        if not user_prompt.strip():
            return LLMResult(
                status=LLMStatus.FAILED,
                error_details="User prompt cannot be empty"
            )
        
        # Initialize client if not already done
        if not self._initialize_client():
            return LLMResult(
                status=LLMStatus.FAILED,
                error_details="Failed to initialize the Anthropic client"
            )
        
        if self._client is None:
            return LLMResult(
                status=LLMStatus.FAILED,
                error_details="Anthropic client is not available"
            )
        
        start_time = time.time()
        
        try:
            # Use provided system prompt or default
            if not system_prompt.strip():
                system_prompt = self.default_system_prompt
            
            # Merge custom parameters with defaults
            generation_params = {
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
            }
            generation_params.update(kwargs)
            
            # Generate response
            self.logger.debug("Generating response via Anthropic API...")
            generation_start = time.time()
            
            response = self._client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                **generation_params
            )
            
            generation_end = time.time()
            
            # Extract the generated text
            generated_text = response.content[0].text
            
            end_time = time.time()
            total_time = end_time - start_time
            generation_time = generation_end - generation_start
            
            self.logger.debug(f"Generation completed in {self._format_time(generation_time)}")
            
            # Extract token count if available
            token_count = None
            if hasattr(response, 'usage') and response.usage:
                token_count = response.usage.output_tokens
            
            return LLMResult(
                status=LLMStatus.SUCCESS,
                response=generated_text,
                generation_time=generation_time,
                token_count=token_count,
                provider_response=response.model_dump() if hasattr(response, 'model_dump') else None
            )
            
        except Exception as e:
            end_time = time.time()
            total_time = end_time - start_time
            self.logger.error(f"Error generating response after {self._format_time(total_time)}: {str(e)}")
            return LLMResult(
                status=LLMStatus.FAILED,
                error_details=f"Error generating response: {str(e)}",
                generation_time=total_time
            )
    
    def test_connection(self) -> LLMResult:
        """
        Test the connection to the Anthropic API by generating a simple response.
        
        Returns:
            LLMResult: Result of the connection test
        """
        if not self.is_configured():
            return LLMResult(
                status=LLMStatus.FAILED,
                error_details="Anthropic provider is not properly configured"
            )
        
        # Test with a simple prompt
        test_prompt = "Hello! Please respond with 'Connection test successful.'"
        result = self.generate(
            system_prompt="You are a helpful assistant. Respond exactly as requested.",
            user_prompt=test_prompt,
            max_tokens=50,
            temperature=0.1
        )
        
        if result.status == LLMStatus.SUCCESS:
            return LLMResult(
                status=LLMStatus.SUCCESS,
                response=f"Connection successful. Model: {self.model}",
                provider_response=result.provider_response
            )
        
        return result
    
    def cleanup(self) -> None:
        """
        Clean up client resources.
        """
        if self._client is not None:
            self._client = None
            self._client_initialized = False
            self.logger.debug(f"Anthropic client resources cleaned up for {self.instance_name}")