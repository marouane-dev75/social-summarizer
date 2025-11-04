"""
Telegram Notification Provider

This module implements the Telegram notification provider using the
Telegram Bot API, adapted for the TimeReclamation project.
"""

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
    
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None, 
                 timeout: Optional[int] = None, retry_attempts: Optional[int] = None):
        """
        Initialize the Telegram provider.
        
        Args:
            bot_token: Telegram bot token (optional, will use config if not provided)
            chat_id: Chat ID to send messages to (optional, will use config if not provided)
            timeout: Request timeout in seconds (optional, will use config if not provided)
            retry_attempts: Number of retry attempts (optional, will use config if not provided)
        """
        self.logger = get_logger()
        
        # Load configuration
        config_manager = get_config_manager()
        telegram_config = config_manager.get_telegram_config()
        
        # Use provided values or fall back to config
        self.bot_token = bot_token or telegram_config.bot_token
        self.chat_id = chat_id or telegram_config.chat_id
        self.timeout = timeout or telegram_config.timeout_seconds
        self.retry_attempts = retry_attempts or telegram_config.retry_attempts
        self.enabled = telegram_config.enabled
        
        self.logger.debug(f"Telegram provider initialized with timeout={self.timeout}, retries={self.retry_attempts}")
    
    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return "Telegram"
    
    def is_configured(self) -> bool:
        """
        Check if the provider is properly configured.
        
        Returns:
            bool: True if the provider is ready to send notifications
        """
        if not self.enabled:
            return False
            
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
    
    def send_message(self, message: str, **kwargs) -> NotificationResult:
        """
        Send a text message via Telegram.
        
        Args:
            message: The message text to send
            **kwargs: Additional parameters:
                - parse_mode: Optional. Send Markdown or HTML formatting
                - chat_id: Optional. Override default chat ID
                
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