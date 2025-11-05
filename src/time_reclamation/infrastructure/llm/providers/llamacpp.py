"""
LlamaCpp LLM Provider

This module implements the LlamaCpp LLM provider using the
llama-cpp-python library, adapted for the TimeReclamation project.
"""

import os
import time
from typing import Optional, Dict, Any
from ..interface import LLMProvider, LLMResult, LLMStatus
from src.time_reclamation.config import get_config_manager
from src.time_reclamation.infrastructure import get_logger


class LlamaCppProvider(LLMProvider):
    """
    LlamaCpp LLM provider implementation.
    
    This class implements the LLMProvider interface for generating
    responses via local GGUF models using llama-cpp-python.
    """
    
    def __init__(self, instance_name: str, config: Dict[str, Any]):
        """
        Initialize the LlamaCpp provider with instance-specific configuration.
        
        Args:
            instance_name: Name of this provider instance
            config: Configuration dictionary for this instance
        """
        self.logger = get_logger()
        self.instance_name = instance_name
        
        # Extract configuration values
        self.model_path = config.get('model_path', '')
        self.context_size = config.get('context_size', 4096)
        self.gpu_layers = config.get('gpu_layers', 0)
        self.generation_config = config.get('generation_config', {})
        self.default_system_prompt = config.get('default_system_prompt', 
            "You are a helpful, harmless, and honest AI assistant.")
        
        # Chat template configuration
        self.chat_template = config.get('chat_template', """<|system|>
{system_prompt}
<|user|>
{user_prompt}
<|assistant|>
""")
        
        # Model instance (lazy loaded)
        self._llm_model = None
        self._model_loaded = False
        
        self.logger.debug(f"LlamaCpp provider '{instance_name}' initialized with model: {self.model_path}")
    
    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return f"LlamaCpp ({self.instance_name})"
    
    def is_configured(self) -> bool:
        """
        Check if the provider is properly configured.
        
        Returns:
            bool: True if the provider is ready to generate responses
        """
        if not self.model_path:
            return False
            
        if not os.path.exists(self.model_path):
            return False
            
        # Check if it's a GGUF file
        if not self.model_path.lower().endswith('.gguf'):
            return False
            
        return True
    
    def _initialize_model(self) -> bool:
        """
        Initialize the LLM model with lazy loading.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        if self._model_loaded:
            return self._llm_model is not None
        
        try:
            # Import llama-cpp-python
            from llama_cpp import Llama
        except ImportError:
            self.logger.error("llama-cpp-python is not installed. Please install it with: pip install llama-cpp-python")
            return False
        
        start_time = time.time()
        
        try:
            self.logger.info(f"Loading model from: {self.model_path}")
            
            # Initialize the model
            self._llm_model = Llama(
                model_path=self.model_path,
                n_ctx=self.context_size,
                n_gpu_layers=self.gpu_layers,
                verbose=False,  # Set to True for debugging
            )
            
            end_time = time.time()
            load_time = end_time - start_time
            self.logger.info(f"Model loaded successfully in {self._format_time(load_time)}!")
            self._model_loaded = True
            return True
            
        except Exception as e:
            end_time = time.time()
            load_time = end_time - start_time
            self.logger.error(f"Error initializing model after {self._format_time(load_time)}: {str(e)}")
            self._model_loaded = True  # Mark as attempted
            return False
    
    def _format_prompt(self, system_prompt: str, user_prompt: str) -> str:
        """
        Format the prompts using the chat template.
        
        Args:
            system_prompt: The system prompt
            user_prompt: The user's input prompt
            
        Returns:
            str: Formatted prompt ready for the model
        """
        return self.chat_template.format(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
    
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
        Generate a response using the LlamaCpp model.
        
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
                error_details="LlamaCpp provider is not properly configured"
            )
        
        if not user_prompt.strip():
            return LLMResult(
                status=LLMStatus.FAILED,
                error_details="User prompt cannot be empty"
            )
        
        # Initialize model if not already done
        if not self._initialize_model():
            return LLMResult(
                status=LLMStatus.FAILED,
                error_details="Failed to initialize the model"
            )
        
        if self._llm_model is None:
            return LLMResult(
                status=LLMStatus.FAILED,
                error_details="Model is not available"
            )
        
        start_time = time.time()
        
        try:
            # Use provided system prompt or default
            if not system_prompt.strip():
                system_prompt = self.default_system_prompt
            
            # Format the prompt
            formatted_prompt = self._format_prompt(system_prompt, user_prompt)
            
            # Merge custom parameters with defaults
            generation_params = {
                "max_tokens": 8000,
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 40,
                "repeat_penalty": 1.1,
                "stop": ["<|file_separator|>"],
                "echo": False,
            }
            generation_params.update(self.generation_config)
            generation_params.update(kwargs)
            
            # Generate response
            self.logger.debug("Generating response...")
            generation_start = time.time()
            response = self._llm_model(
                formatted_prompt,
                **generation_params
            )
            generation_end = time.time()
            
            # Extract the generated text
            generated_text = response['choices'][0]['text'].strip()
            
            end_time = time.time()
            total_time = end_time - start_time
            generation_time = generation_end - generation_start
            
            self.logger.debug(f"Generation completed in {self._format_time(generation_time)}")
            
            return LLMResult(
                status=LLMStatus.SUCCESS,
                response=generated_text,
                generation_time=generation_time,
                provider_response=response
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
        Test the connection to the LlamaCpp model by generating a simple response.
        
        Returns:
            LLMResult: Result of the connection test
        """
        if not self.is_configured():
            return LLMResult(
                status=LLMStatus.FAILED,
                error_details="LlamaCpp provider is not properly configured"
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
                response=f"Connection successful. Model: {os.path.basename(self.model_path)}",
                provider_response=result.provider_response
            )
        
        return result
    
    def cleanup(self) -> None:
        """
        Clean up model resources.
        """
        if self._llm_model is not None:
            del self._llm_model
            self._llm_model = None
            self._model_loaded = False
            self.logger.debug(f"Model resources cleaned up for {self.instance_name}")