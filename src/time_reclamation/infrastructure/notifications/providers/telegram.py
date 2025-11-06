"""
Telegram Notification Provider

This module implements the Telegram notification provider using the
Telegram Bot API, adapted for the TimeReclamation project.
"""

import os
import requests
from typing import Optional, Dict, Any
from ..interface import NotificationProvider, NotificationResult, NotificationStatus
from src.time_reclamation.config import get_config_manager
from src.time_reclamation.infrastructure import get_logger


class TelegramProvider(NotificationProvider):
    """
    Telegram notification provider implementation.
    
    This class implements the NotificationProvider interface for sending
    notifications via Telegram Bot API.
    """
    
    BASE_URL = "https://api.telegram.org/bot"
    
    def __init__(self, instance_name: str, config: Dict[str, Any]):
        """
        Initialize the Telegram provider with instance-specific configuration.
        
        Args:
            instance_name: Name of this provider instance
            config: Configuration dictionary for this instance
        """
        self.logger = get_logger()
        self.instance_name = instance_name
        
        # Extract configuration values
        self.bot_token = config.get('bot_token', 'YOUR_BOT_TOKEN_HERE')
        self.chat_id = config.get('chat_id', 'YOUR_CHAT_ID_HERE')
        self.timeout = config.get('timeout_seconds', 30)
        self.retry_attempts = config.get('retry_attempts', 3)
        
        self.logger.debug(f"Telegram provider '{instance_name}' initialized with timeout={self.timeout}, retries={self.retry_attempts}")
    
    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return f"Telegram ({self.instance_name})"
    
    def is_configured(self) -> bool:
        """
        Check if the provider is properly configured.
        
        Returns:
            bool: True if the provider is ready to send notifications
        """
        if not self.bot_token or self.bot_token == "YOUR_BOT_TOKEN_HERE":
            return False
            
        if not self.chat_id or self.chat_id == "YOUR_CHAT_ID_HERE":
            return False
            
        return self._is_valid_token(self.bot_token)
    
    def _is_valid_token(self, token: str) -> bool:
        """
        Validate bot token format.
        
        Args:
            token: Bot token to validate
            
        Returns:
            bool: True if token format is valid
        """
        if not token or token == "YOUR_BOT_TOKEN_HERE":
            return False
        
        # Basic format check: should contain numbers and letters with colon
        parts = token.split(":")
        return len(parts) == 2 and parts[0].isdigit() and len(parts[1]) > 0
    
    def _build_url(self, method: str) -> str:
        """
        Build API URL for a specific method.
        
        Args:
            method: Telegram Bot API method name
            
        Returns:
            str: Complete API URL
        """
        return f"{self.BASE_URL}{self.bot_token}/{method}"
    
    def _make_request(self, method: str, data: Dict[str, Any]) -> NotificationResult:
        """
        Make HTTP request to Telegram API with retry logic.
        
        Args:
            method: Telegram Bot API method name
            data: Request payload
            
        Returns:
            NotificationResult: Result of the API call
        """
        url = self._build_url(method)
        
        for attempt in range(self.retry_attempts):
            try:
                self.logger.debug(f"Making request to {method} (attempt {attempt + 1})")
                
                response = requests.post(
                    url,
                    json=data,
                    timeout=self.timeout,
                    headers={'Content-Type': 'application/json'}
                )
                
                # Parse JSON response
                try:
                    response_data = response.json()
                except ValueError:
                    return NotificationResult(
                        status=NotificationStatus.FAILED,
                        error_details="Invalid JSON response from Telegram API"
                    )
                
                # Check if request was successful
                if response_data.get('ok', False):
                    self.logger.debug(f"Request to {method} successful")
                    return NotificationResult(
                        status=NotificationStatus.SUCCESS,
                        message="Message sent successfully",
                        provider_response=response_data.get('result')
                    )
                else:
                    error_msg = response_data.get('description', 'Unknown error')
                    self.logger.warning(f"Telegram API error: {error_msg}")
                    return NotificationResult(
                        status=NotificationStatus.FAILED,
                        error_details=error_msg,
                        provider_response=response_data
                    )
                    
            except requests.exceptions.Timeout:
                self.logger.warning(f"Request timeout (attempt {attempt + 1})")
                if attempt == self.retry_attempts - 1:
                    return NotificationResult(
                        status=NotificationStatus.FAILED,
                        error_details="Request timeout after all retry attempts"
                    )
                    
            except requests.exceptions.ConnectionError:
                self.logger.warning(f"Connection error (attempt {attempt + 1})")
                if attempt == self.retry_attempts - 1:
                    return NotificationResult(
                        status=NotificationStatus.FAILED,
                        error_details="Connection error after all retry attempts"
                    )
                    
            except Exception as e:
                self.logger.error(f"Unexpected error: {str(e)}")
                return NotificationResult(
                    status=NotificationStatus.FAILED,
                    error_details=f"Unexpected error: {str(e)}"
                )
        
        return NotificationResult(
            status=NotificationStatus.FAILED,
            error_details="All retry attempts failed"
        )
    
    def send_message(self, message: str, audio_file: Optional[str] = None, **kwargs) -> NotificationResult:
        """
        Send a text message via Telegram, optionally with an audio file.
        
        When an audio file is provided, the message is sent as the audio caption,
        combining both into a single Telegram message for efficiency.
        
        Args:
            message: The message text to send (or audio caption if audio_file provided)
            audio_file: Optional path to audio file to send with message as caption
            **kwargs: Additional parameters:
                - parse_mode: Optional. Send Markdown or HTML formatting
                - chat_id: Optional. Override default chat ID
                - audio_caption: Optional. Override caption for audio file (defaults to message)
                - audio_title: Optional. Title for audio file
                - audio_performer: Optional. Performer for audio file
                
        Returns:
            NotificationResult: Result of the notification attempt
        """
        # If no audio file, send text message only
        if not audio_file:
            return self._send_text_message(message, **kwargs)
        
        # If audio file provided, send audio with message as caption
        # Use audio_caption if explicitly provided, otherwise use message
        if 'audio_caption' not in kwargs:
            kwargs['audio_caption'] = message
        
        return self._send_audio_file(audio_file, **kwargs)
    
    def _send_text_message(self, message: str, **kwargs) -> NotificationResult:
        """
        Send a text message via Telegram.
        
        Args:
            message: The message text to send
            **kwargs: Additional parameters
                
        Returns:
            NotificationResult: Result of the notification attempt
        """
        if not self.is_configured():
            return NotificationResult(
                status=NotificationStatus.FAILED,
                error_details="Telegram provider is not properly configured"
            )
        
        if not message.strip():
            return NotificationResult(
                status=NotificationStatus.FAILED,
                error_details="Message text cannot be empty"
            )
        
        # Use provided chat_id or default
        chat_id = kwargs.get('chat_id', self.chat_id)
        
        data = {
            'chat_id': chat_id,
            'text': message
        }
        
        # Add optional parameters
        if 'parse_mode' in kwargs:
            data['parse_mode'] = kwargs['parse_mode']
        
        return self._make_request('sendMessage', data)
    
    def _send_audio_file(self, file_path: str, **kwargs) -> NotificationResult:
        """
        Send an audio file via Telegram sendAudio API.
        
        Args:
            file_path: Path to the audio file
            **kwargs: Additional parameters
                
        Returns:
            NotificationResult: Result of the send attempt
        """
        if not self.is_configured():
            return NotificationResult(
                status=NotificationStatus.FAILED,
                error_details="Telegram provider is not properly configured"
            )
        
        # Validate file exists
        if not os.path.exists(file_path):
            return NotificationResult(
                status=NotificationStatus.FAILED,
                error_details=f"Audio file not found: {file_path}"
            )
        
        # Check file size (50MB Telegram limit)
        file_size = os.path.getsize(file_path)
        MAX_SIZE = 50 * 1024 * 1024  # 50 MB
        if file_size > MAX_SIZE:
            return NotificationResult(
                status=NotificationStatus.FAILED,
                error_details=f"File too large: {file_size / 1024 / 1024:.1f}MB (max 50MB)"
            )
        
        # Prepare request
        chat_id = kwargs.get('chat_id', self.chat_id)
        url = self._build_url('sendAudio')
        
        # Retry logic
        for attempt in range(self.retry_attempts):
            try:
                self.logger.debug(f"Sending audio file (attempt {attempt + 1}): {file_path}")
                
                with open(file_path, 'rb') as audio:
                    files = {'audio': audio}
                    data = {
                        'chat_id': chat_id,
                    }
                    
                    # Add optional caption
                    if 'audio_caption' in kwargs:
                        data['caption'] = kwargs['audio_caption']
                    
                    # Add optional metadata
                    if 'audio_title' in kwargs:
                        data['title'] = kwargs['audio_title']
                    if 'audio_performer' in kwargs:
                        data['performer'] = kwargs['audio_performer']
                    
                    response = requests.post(
                        url,
                        files=files,
                        data=data,
                        timeout=self.timeout
                    )
                    
                    # Parse JSON response
                    try:
                        response_data = response.json()
                    except ValueError:
                        if attempt == self.retry_attempts - 1:
                            return NotificationResult(
                                status=NotificationStatus.FAILED,
                                error_details="Invalid JSON response from Telegram API"
                            )
                        continue
                    
                    # Check if request was successful
                    if response_data.get('ok', False):
                        self.logger.debug("Audio file sent successfully")
                        return NotificationResult(
                            status=NotificationStatus.SUCCESS,
                            message="Audio sent successfully",
                            provider_response=response_data.get('result')
                        )
                    else:
                        error_msg = response_data.get('description', 'Unknown error')
                        self.logger.warning(f"Telegram API error: {error_msg}")
                        if attempt == self.retry_attempts - 1:
                            return NotificationResult(
                                status=NotificationStatus.FAILED,
                                error_details=error_msg,
                                provider_response=response_data
                            )
                        
            except requests.exceptions.Timeout:
                self.logger.warning(f"Request timeout (attempt {attempt + 1})")
                if attempt == self.retry_attempts - 1:
                    return NotificationResult(
                        status=NotificationStatus.FAILED,
                        error_details="Request timeout after all retry attempts"
                    )
                    
            except requests.exceptions.ConnectionError:
                self.logger.warning(f"Connection error (attempt {attempt + 1})")
                if attempt == self.retry_attempts - 1:
                    return NotificationResult(
                        status=NotificationStatus.FAILED,
                        error_details="Connection error after all retry attempts"
                    )
                    
            except Exception as e:
                self.logger.error(f"Unexpected error: {str(e)}")
                return NotificationResult(
                    status=NotificationStatus.FAILED,
                    error_details=f"Unexpected error: {str(e)}"
                )
        
        return NotificationResult(
            status=NotificationStatus.FAILED,
            error_details="All retry attempts failed"
        )
    
    def test_connection(self) -> NotificationResult:
        """
        Test the connection to Telegram by getting bot information.
        
        Returns:
            NotificationResult: Result of the connection test
        """
        if not self.is_configured():
            return NotificationResult(
                status=NotificationStatus.FAILED,
                error_details="Telegram provider is not properly configured"
            )
        
        result = self._make_request('getMe', {})
        
        if result.status == NotificationStatus.SUCCESS:
            bot_info = result.provider_response
            bot_name = bot_info.get('username', 'Unknown') if bot_info else 'Unknown'
            return NotificationResult(
                status=NotificationStatus.SUCCESS,
                message=f"Connection successful. Bot: @{bot_name}",
                provider_response=result.provider_response
            )
        
        return result