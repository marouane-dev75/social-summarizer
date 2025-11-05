"""TTS infrastructure package."""

from .interface import TTSProvider, TTSResult, TTSStatus
from .manager import TTSManager, get_tts_manager, generate_speech

__all__ = [
    'TTSProvider',
    'TTSResult',
    'TTSStatus',
    'TTSManager',
    'get_tts_manager',
    'generate_speech',
]