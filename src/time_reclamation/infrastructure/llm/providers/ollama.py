"""
Ollama LLM Provider

This module implements the Ollama LLM provider using the
official ollama Python library for local and remote Ollama instances.
"""

import time
from typing import Optional, Dict, Any
from ..interface import LLMProvider, LLMResult, LLMStatus
from src.time_reclamation.config import get_config_manager
from src.time_reclamation.infrastructure import get_logger


class OllamaProvider(LLMProvider):
    """
    Ollama LLM provider implementation.
    
    This class implements the LLMProvider interface for generating
    responses via Ollama models (local or remote instances).
    """
    
    def __init__(self, instance_name: str, config: Dict[str, Any]):
        """
        Initialize the Ollama provider with instance-specific configuration.
        
        Args:
            instance_name: Name of this provider instance
            config: Configuration dictionary for this instance
        """
        self.logger = get_logger()
        self.instance_name = instance_name
        
        # Extract configuration values
        self.base_url = config.get('base_url', 'http://localhost:11434')
        self.model = config.get('model', 'llama2')
        self.timeout_seconds = config.get('timeout_seconds', 120)
        self.generation_config = config.get('generation_config', {})
        self.default_system_prompt = config.get('default_system_prompt', 
            "You are a helpful AI assistant.")
        
        # Client instance (lazy loaded)
        self._client = None
        self._client_initialized = False
        
        self.logger.debug(f"Ollama provider '{instance_name}' initialized with model: {self.model} at {self.base_url}")
    
    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return f"Ollama ({self.instance_name})"
    
    def is_configured(self) -> bool:
        """
        Check if the provider is properly configured.
        
        Returns:
            bool: True if the provider is ready to generate responses
        """
        if not self.base_url:
            return False
            
        if not self.model:
            return False
            
        # Check for placeholder values
        if self.model in ['your-model-name-here', 'YOUR_MODEL_NAME_HERE']:
            return False
            
        return True
    
    def _initialize_client(self) -> bool:
        """
        Initialize the Ollama client with lazy loading.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        if self._client_initialized:
            return self._client is not None
        
        try:
            # Import ollama
            import ollama
        except ImportError:
            self.logger.error("ollama library is not installed. Please install it with: pip install ollama")
            self._client_initialized = True
            return False
        
        try:
            self.logger.debug(f"Initializing Ollama client for model: {self.model} at {self.base_url}")
            
            # Initialize the client with custom host
            self._client = ollama.Client(host=self.base_url)
            
            self.logger.debug("Ollama client initialized successfully")
            self._client_initialized = True
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing Ollama client: {str(e)}")
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
        Generate a response using the Ollama model.
        
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
                error_details="Ollama provider is not properly configured"
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
                error_details="Failed to initialize the Ollama client"
            )
        
        if self._client is None:
            return LLMResult(
                status=LLMStatus.FAILED,
                error_details="Ollama client is not available"
            )
        
        start_time = time.time()
        
        try:
            # Use provided system prompt or default
            if not system_prompt.strip():
                system_prompt = self.default_system_prompt
            
            # Prepare messages in chat format
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Merge custom parameters with defaults
            generation_params = {
                "temperature": 0.7,
                "num_predict": 4000,  # Ollama's equivalent to max_tokens
                "top_p": 0.9,
                "top_k": 40,
            }
            generation_params.update(self.generation_config)
            generation_params.update(kwargs)
            
            # Map common parameter names to Ollama's naming
            if 'max_tokens' in generation_params:
                generation_params['num_predict'] = generation_params.pop('max_tokens')
            
            # Generate response
            self.logger.debug(f"Generating response via Ollama API at {self.base_url}...")
            generation_start = time.time()
            
            response = self._client.chat(
                model=self.model,
                messages=messages,
                options=generation_params,
                stream=False
            )
            
            generation_end = time.time()
            
            # Extract the generated text
            generated_text = response['message']['content']
            
            end_time = time.time()
            total_time = end_time - start_time
            generation_time = generation_end - generation_start
            
            self.logger.debug(f"Generation completed in {self._format_time(generation_time)}")
            
            # Extract token count if available
            token_count = None
            if 'eval_count' in response:
                token_count = response['eval_count']
            
            return LLMResult(
                status=LLMStatus.SUCCESS,
                response=generated_text,
                generation_time=generation_time,
                token_count=token_count,
                provider_response=response
            )
            
        except Exception as e:
            end_time = time.time()
            total_time = end_time - start_time
            error_msg = str(e)
            
            # Provide helpful error messages for common issues
            if "connection" in error_msg.lower() or "refused" in error_msg.lower():
                error_msg = f"Cannot connect to Ollama server at {self.base_url}. Make sure Ollama is running."
            elif "model" in error_msg.lower() and "not found" in error_msg.lower():
                error_msg = f"Model '{self.model}' not found. Pull it first with: ollama pull {self.model}"
            
            self.logger.error(f"Error generating response after {self._format_time(total_time)}: {error_msg}")
            return LLMResult(
                status=LLMStatus.FAILED,
                error_details=f"Error generating response: {error_msg}",
                generation_time=total_time
            )
    
    def test_connection(self) -> LLMResult:
        """
        Test the connection to the Ollama server by generating a simple response.
        
        Returns:
            LLMResult: Result of the connection test
        """
        if not self.is_configured():
            return LLMResult(
                status=LLMStatus.FAILED,
                error_details="Ollama provider is not properly configured"
            )
        
        # Initialize client if not already done
        if not self._initialize_client():
            return LLMResult(
                status=LLMStatus.FAILED,
                error_details="Failed to initialize the Ollama client"
            )
        
        if self._client is None:
            return LLMResult(
                status=LLMStatus.FAILED,
                error_details="Ollama client is not available"
            )
        
        try:
            # First, check if the model is available
            self.logger.debug(f"Checking if model '{self.model}' is available...")
            models_response = self._client.list()
            available_models = [model['name'] for model in models_response.get('models', [])]
            
            if not any(self.model in model_name for model_name in available_models):
                return LLMResult(
                    status=LLMStatus.FAILED,
                    error_details=f"Model '{self.model}' is not available. Available models: {', '.join(available_models)}. Pull it with: ollama pull {self.model}"
                )
            
            # Test with a simple prompt
            test_prompt = "Hello! Please respond with 'Connection test successful.'"
            result = self.generate(
                system_prompt="You are a helpful assistant. Respond exactly as requested.",
                user_prompt=test_prompt,
                num_predict=50,
                temperature=0.1
            )
            
            if result.status == LLMStatus.SUCCESS:
                return LLMResult(
                    status=LLMStatus.SUCCESS,
                    response=f"Connection successful. Model: {self.model} at {self.base_url}",
                    provider_response=result.provider_response
                )
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            if "connection" in error_msg.lower() or "refused" in error_msg.lower():
                error_msg = f"Cannot connect to Ollama server at {self.base_url}. Make sure Ollama is running with: ollama serve"
            
            return LLMResult(
                status=LLMStatus.FAILED,
                error_details=error_msg
            )
    
    def cleanup(self) -> None:
        """
        Clean up client resources.
        """
        if self._client is not None:
            self._client = None
            self._client_initialized = False
            self.logger.debug(f"Ollama client resources cleaned up for {self.instance_name}")