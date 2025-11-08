"""
Kokoro TTS Provider

This module implements the Kokoro TTS provider using the
kokoro library, adapted for the TimeReclamation project.
"""

import os
import time
from typing import Optional, Dict, Any
from pathlib import Path
from ..interface import TTSProvider, TTSResult, TTSStatus
from src.time_reclamation.config import get_config_manager
from src.time_reclamation.infrastructure import get_logger


class KokoroProvider(TTSProvider):
    """
    Kokoro TTS provider implementation.
    
    This class implements the TTSProvider interface for generating
    speech using the Kokoro-82M model.
    """
    
    def __init__(self, instance_name: str, config: Dict[str, Any]):
        """
        Initialize the Kokoro provider with instance-specific configuration.
        
        Args:
            instance_name: Name of this provider instance
            config: Configuration dictionary for this instance
        """
        self.logger = get_logger()
        self.instance_name = instance_name
        
        # Extract configuration values
        self.voice = config.get('voice', 'af_alloy')
        self.lang_code = config.get('lang_code', 'a')
        self.repo_id = config.get('repo_id', 'hexgrad/Kokoro-82M')
        self.sample_rate = config.get('sample_rate', 24000)
        self.output_dir = config.get('output_dir', 'cache_data/tts')
        self.device = config.get('device', 'cpu')  # Default to CPU for compatibility
        
        # Pipeline instance (lazy loaded)
        self._pipeline = None
        self._pipeline_loaded = False
        
        self.logger.debug(f"Kokoro provider '{instance_name}' initialized with voice: {self.voice}")
    
    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return f"Kokoro ({self.instance_name})"
    
    def is_configured(self) -> bool:
        """
        Check if the provider is properly configured.
        
        Returns:
            bool: True if the provider is ready to generate speech
        """
        # Basic validation
        if not self.voice:
            return False
        if not self.lang_code:
            return False
        if not self.repo_id:
            return False
        
        return True
    
    def _initialize_pipeline(self) -> bool:
        """
        Initialize the Kokoro pipeline with lazy loading.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        if self._pipeline_loaded:
            return self._pipeline is not None
        
        try:
            # Import kokoro
            from kokoro import KPipeline
        except ImportError:
            self.logger.error("kokoro is not installed. Please install it with: pip install kokoro")
            return False
        
        start_time = time.time()
        
        try:
            self.logger.info(f"Loading Kokoro pipeline with voice '{self.voice}' on device '{self.device}'...")
            
            # Initialize the pipeline
            self._pipeline = KPipeline(
                lang_code=self.lang_code,
                repo_id=self.repo_id,
                device=self.device
            )
            
            end_time = time.time()
            load_time = end_time - start_time
            self.logger.info(f"Kokoro pipeline loaded successfully in {self._format_time(load_time)}!")
            self._pipeline_loaded = True
            return True
            
        except Exception as e:
            end_time = time.time()
            load_time = end_time - start_time
            self.logger.error(f"Error initializing Kokoro pipeline after {self._format_time(load_time)}: {str(e)}")
            self._pipeline_loaded = True  # Mark as attempted
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
                error_details="Kokoro provider is not properly configured"
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
        
        # Initialize pipeline if not already done
        if not self._initialize_pipeline():
            return TTSResult(
                status=TTSStatus.FAILED,
                error_details="Failed to initialize the Kokoro pipeline"
            )
        
        if self._pipeline is None:
            return TTSResult(
                status=TTSStatus.FAILED,
                error_details="Kokoro pipeline is not available"
            )
        
        start_time = time.time()
        
        try:
            import soundfile as sf
            import numpy as np
            
            # Generate audio chunks
            self.logger.debug(f"Generating speech for text: {text[:50]}...")
            generation_start = time.time()
            
            generator = self._pipeline(text, voice=self.voice)
            
            # Collect all audio chunks
            audio_chunks = []
            chunk_count = 0
            
            for i, (gs, ps, audio) in enumerate(generator):
                self.logger.debug(f"Chunk {i}: gs={gs}, ps={ps}, samples={len(audio)}")
                audio_chunks.append(audio)
                chunk_count += 1
            
            generation_end = time.time()
            generation_time = generation_end - generation_start
            
            # Combine all chunks into a single audio array
            if not audio_chunks:
                return TTSResult(
                    status=TTSStatus.FAILED,
                    error_details="No audio chunks generated",
                    generation_time=generation_time
                )
            
            combined_audio = np.concatenate(audio_chunks)
            
            # Calculate audio duration
            audio_duration = len(combined_audio) / self.sample_rate
            
            # Save combined audio to file
            output_path = Path(self.output_dir) / output_filename
            sf.write(str(output_path), combined_audio, self.sample_rate)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            self.logger.info(f"Speech generated successfully in {self._format_time(generation_time)}")
            self.logger.info(f"Audio duration: {audio_duration:.2f}s, Chunks: {chunk_count}")
            self.logger.info(f"Saved to: {output_path}")
            
            return TTSResult(
                status=TTSStatus.SUCCESS,
                output_file=str(output_path),
                generation_time=generation_time,
                audio_duration=audio_duration,
                provider_response={
                    'chunks': chunk_count,
                    'samples': len(combined_audio),
                    'sample_rate': self.sample_rate
                }
            )
            
        except ImportError as e:
            end_time = time.time()
            total_time = end_time - start_time
            self.logger.error(f"Missing dependency: {str(e)}")
            return TTSResult(
                status=TTSStatus.FAILED,
                error_details=f"Missing dependency: {str(e)}. Please install: pip install soundfile numpy",
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
                error_details="Kokoro provider is not properly configured"
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
                    'message': f"Connection successful. Voice: {self.voice}, Language: {self.lang_code}",
                    'test_duration': result.audio_duration
                }
            )
        
        return result
    
    def cleanup(self) -> None:
        """
        Clean up pipeline resources.
        """
        if self._pipeline is not None:
            del self._pipeline
            self._pipeline = None
            self._pipeline_loaded = False
            self.logger.debug(f"Kokoro pipeline resources cleaned up for {self.instance_name}")