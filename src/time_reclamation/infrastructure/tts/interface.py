"""
TTS Interface Module

This module defines the abstract interface for TTS providers,
allowing easy switching between different text-to-speech services.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class TTSStatus(Enum):
    """Status of a TTS operation."""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"


@dataclass
class TTSResult:
    """Result of a TTS generation attempt."""
    status: TTSStatus
    output_file: Optional[str] = None
    error_details: Optional[str] = None
    generation_time: Optional[float] = None
    audio_duration: Optional[float] = None
    provider_response: Optional[Dict[str, Any]] = None


class TTSProvider(ABC):
    """
    Abstract base class for TTS providers.
    
    This interface defines the contract that all TTS providers
    must implement, ensuring consistency across different services.
    """
    
    @abstractmethod
    def generate_speech(self, text: str, output_filename: str) -> TTSResult:
        """
        Generate speech from text and save to file.
        
        Args:
            text: The text to convert to speech
            output_filename: Name of the output file (without path)
            
        Returns:
            TTSResult: Result of the generation attempt
        """
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """
        Check if the provider is properly configured.
        
        Returns:
            bool: True if the provider is ready to generate speech
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> TTSResult:
        """
        Test the TTS provider with a simple phrase.
        
        Returns:
            TTSResult: Result of the connection test
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Get the name of the TTS provider.
        
        Returns:
            str: Provider name (e.g., "Kokoro", "Coqui", etc.)
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """
        Clean up provider resources (models, connections, etc.).
        """
        pass