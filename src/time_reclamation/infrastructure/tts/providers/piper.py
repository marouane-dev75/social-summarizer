"""
Piper TTS Provider

This module implements the Piper TTS provider using the
piper-tts library, adapted for the TimeReclamation project.
"""

import os
import time
import wave
from typing import Optional, Dict, Any
from pathlib import Path
from ..interface import TTSProvider, TTSResult, TTSStatus
from src.time_reclamation.config import get_config_manager
from src.time_reclamation.infrastructure import get_logger


class PiperProvider(TTSProvider):
    """
    Piper TTS provider implementation.
    
    This class implements the TTSProvider interface for generating
    speech using Piper TTS with ONNX models.
    """
    
    def __init__(self, instance_name: str, config: Dict[str, Any]):
        """
        Initialize the Piper provider with instance-specific configuration.
        
        Args:
            instance_name: Name of this provider instance
            config: Configuration dictionary for this instance
        """
        self.logger = get_logger()
        self.instance_name = instance_name
        
        # Extract configuration values
        self.model_path = config.get('model_path', '')
        self.output_dir = config.get('output_dir', 'cache_data/tts')
        
        # Voice instance (lazy loaded)
        self._voice = None
        self._voice_loaded = False
        
        self.logger.debug(f"Piper provider '{instance_name}' initialized with model: {self.model_path}")
    
    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return f"Piper ({self.instance_name})"
    
    def is_configured(self) -> bool:
        """
        Check if the provider is properly configured.
        
        Returns:
            bool: True if the provider is ready to generate speech
        """
        # Check if model path is provided
        if not self.model_path:
            return False
        
        # Check if model file exists
        model_file = Path(self.model_path)
        if not model_file.exists():
            self.logger.warning(f"Model file not found: {self.model_path}")
            return False
        
        # Check if model config file exists (.onnx.json)
        config_file = Path(str(self.model_path) + '.json')
        if not config_file.exists():
            self.logger.warning(f"Model config file not found: {config_file}")
            return False
        
        return True
    
    def _initialize_voice(self) -> bool:
        """
        Initialize the Piper voice with lazy loading.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        if self._voice_loaded:
            return self._voice is not None
        
        try:
            # Import piper
            from piper import PiperVoice
        except ImportError:
            self.logger.error("piper-tts is not installed. Please install it with: pip install piper-tts")
            return False
        
        start_time = time.time()
        
        try:
            self.logger.info(f"Loading Piper voice model from '{self.model_path}'...")
            
            # Load the voice model
            self._voice = PiperVoice.load(self.model_path)
            
            end_time = time.time()
            load_time = end_time - start_time
            self.logger.info(f"Piper voice model loaded successfully in {self._format_time(load_time)}!")
            self._voice_loaded = True
            return True
            
        except Exception as e:
            end_time = time.time()
            load_time = end_time - start_time
            self.logger.error(f"Error initializing Piper voice after {self._format_time(load_time)}: {str(e)}")
            self._voice_loaded = True  # Mark as attempted
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
    
    def _ensure_output_directory(self) -> bool:
        """
        Ensure the output directory exists.
        
        Returns:
            bool: True if directory exists or was created successfully
        """
        try:
            output_path = Path(self.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            self.logger.error(f"Failed to create output directory '{self.output_dir}': {str(e)}")
            return False
    
    def generate_speech(self, text: str, output_filename: str) -> TTSResult:
        """
        Generate speech from text and save to file.
        
        Args:
            text: The text to convert to speech
            output_filename: Name of the output file (without path)
            
        Returns:
            TTSResult: Result of the generation attempt
        """
        if not self.is_configured():
            return TTSResult(
                status=TTSStatus.FAILED,
                error_details="Piper provider is not properly configured"
            )
        
        if not text.strip():
            return TTSResult(
                status=TTSStatus.FAILED,
                error_details="Text cannot be empty"
            )
        
        # Ensure output directory exists
        if not self._ensure_output_directory():
            return TTSResult(
                status=TTSStatus.FAILED,
                error_details=f"Failed to create output directory: {self.output_dir}"
            )
        
        # Initialize voice if not already done
        if not self._initialize_voice():
            return TTSResult(
                status=TTSStatus.FAILED,
                error_details="Failed to initialize the Piper voice model"
            )
        
        if self._voice is None:
            return TTSResult(
                status=TTSStatus.FAILED,
                error_details="Piper voice model is not available"
            )
        
        start_time = time.time()
        
        try:
            # Generate audio and save to file
            self.logger.debug(f"Generating speech for text: {text[:50]}...")
            generation_start = time.time()
            
            output_path = Path(self.output_dir) / output_filename
            
            # Use Piper's synthesize method to write directly to WAV file
            with wave.open(str(output_path), "wb") as wav_file:
                self._voice.synthesize_wav(text, wav_file)
            
            generation_end = time.time()
            generation_time = generation_end - generation_start
            
            # Calculate audio duration from the WAV file
            audio_duration = None
            try:
                with wave.open(str(output_path), "rb") as wav_file:
                    frames = wav_file.getnframes()
                    rate = wav_file.getframerate()
                    audio_duration = frames / float(rate)
            except Exception as e:
                self.logger.warning(f"Could not calculate audio duration: {str(e)}")
            
            end_time = time.time()
            total_time = end_time - start_time
            
            self.logger.info(f"Speech generated successfully in {self._format_time(generation_time)}")
            if audio_duration:
                self.logger.info(f"Audio duration: {audio_duration:.2f}s")
            self.logger.info(f"Saved to: {output_path}")
            
            return TTSResult(
                status=TTSStatus.SUCCESS,
                output_file=str(output_path),
                generation_time=generation_time,
                audio_duration=audio_duration,
                provider_response={
                    'model_path': self.model_path,
                    'total_time': total_time
                }
            )
            
        except ImportError as e:
            end_time = time.time()
            total_time = end_time - start_time
            self.logger.error(f"Missing dependency: {str(e)}")
            return TTSResult(
                status=TTSStatus.FAILED,
                error_details=f"Missing dependency: {str(e)}. Please install: pip install piper-tts",
                generation_time=total_time
            )
        except Exception as e:
            end_time = time.time()
            total_time = end_time - start_time
            self.logger.error(f"Error generating speech after {self._format_time(total_time)}: {str(e)}")
            return TTSResult(
                status=TTSStatus.FAILED,
                error_details=f"Error generating speech: {str(e)}",
                generation_time=total_time
            )
    
    def test_connection(self) -> TTSResult:
        """
        Test the TTS provider with a simple phrase.
        
        Returns:
            TTSResult: Result of the connection test
        """
        if not self.is_configured():
            return TTSResult(
                status=TTSStatus.FAILED,
                error_details="Piper provider is not properly configured"
            )
        
        # Test with a simple phrase
        test_text = "Hello! This is a connection test."
        test_filename = f"test_{self.instance_name}_{int(time.time())}.wav"
        
        result = self.generate_speech(test_text, test_filename)
        
        if result.status == TTSStatus.SUCCESS:
            # Clean up test file
            try:
                if result.output_file and os.path.exists(result.output_file):
                    os.remove(result.output_file)
                    self.logger.debug(f"Cleaned up test file: {result.output_file}")
            except Exception as e:
                self.logger.warning(f"Failed to clean up test file: {str(e)}")
            
            return TTSResult(
                status=TTSStatus.SUCCESS,
                output_file=None,
                generation_time=result.generation_time,
                audio_duration=result.audio_duration,
                provider_response={
                    'message': f"Connection successful. Model: {Path(self.model_path).name}",
                    'test_duration': result.audio_duration
                }
            )
        
        return result
    
    def cleanup(self) -> None:
        """
        Clean up voice resources.
        """
        if self._voice is not None:
            del self._voice
            self._voice = None
            self._voice_loaded = False
            self.logger.debug(f"Piper voice resources cleaned up for {self.instance_name}")