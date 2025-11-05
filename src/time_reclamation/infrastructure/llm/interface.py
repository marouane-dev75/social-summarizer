"""
LLM Interface Module

This module defines the abstract interface for LLM providers,
allowing easy switching between different language model services.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class LLMStatus(Enum):
    """Status of an LLM operation."""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"


@dataclass
class LLMResult:
    """Result of an LLM generation attempt."""
    status: LLMStatus
    response: Optional[str] = None
    error_details: Optional[str] = None
    provider_response: Optional[Dict[str, Any]] = None
    generation_time: Optional[float] = None
    token_count: Optional[int] = None


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    This interface defines the contract that all LLM providers
    must implement, ensuring consistency across different services.
    """
    
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> LLMResult:
        """
        Generate a response using the LLM.
        
        Args:
            system_prompt: The system prompt to set context/behavior
            user_prompt: The user's input prompt
            **kwargs: Provider-specific parameters
            
        Returns:
            LLMResult: Result of the generation attempt
        """
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """
        Check if the provider is properly configured.
        
        Returns:
            bool: True if the provider is ready to generate responses
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> LLMResult:
        """
        Test the connection to the LLM service.
        
        Returns:
            LLMResult: Result of the connection test
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Get the name of the LLM provider.
        
        Returns:
            str: Provider name (e.g., "LlamaCpp", "OpenAI", "Anthropic")
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """
        Clean up provider resources (models, connections, etc.).
        """
        pass