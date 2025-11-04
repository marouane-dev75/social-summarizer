"""Configuration manager for Time Reclamation App."""

from dataclasses import dataclass
from typing import Optional
import os
import yaml
from pathlib import Path


@dataclass
class DatabaseConfig:
    """Database configuration data class."""
    path: str = "cache_data/state.db"
    auto_create: bool = True


@dataclass
class TelegramConfig:
    """Telegram notification configuration data class."""
    enabled: bool = False
    bot_token: str = "YOUR_BOT_TOKEN_HERE"
    chat_id: str = "YOUR_CHAT_ID_HERE"
    timeout_seconds: int = 30
    retry_attempts: int = 3


@dataclass
class NotificationConfig:
    """Notification configuration data class."""
    telegram: TelegramConfig = None
    
    def __post_init__(self):
        """Initialize nested configurations."""
        if self.telegram is None:
            self.telegram = TelegramConfig()


@dataclass
class AppConfig:
    """Application configuration data class."""
    name: str = "Time Reclamation App"
    version: str = "1.0.0"
    description: str = "Reclaim time wasted on social media by getting curated summaries instead of endless scrolling"
    author: str = "Time Reclamation Team"
    database: DatabaseConfig = None
    notifications: NotificationConfig = None
    
    def __post_init__(self):
        """Initialize nested configurations."""
        if self.database is None:
            self.database = DatabaseConfig()
        if self.notifications is None:
            self.notifications = NotificationConfig()


class ConfigManager:
    """Manages application configuration."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to configuration file (optional)
        """
        self.config_path = config_path or self._get_default_config_path()
        self._config: Optional[AppConfig] = None
    
    def _get_default_config_path(self) -> str:
        """Get the default configuration file path."""
        # Look for config.yml in the config directory
        config_dir = Path(__file__).parent
        return str(config_dir / "config.yml")
    
    def get_config(self) -> AppConfig:
        """
        Get the application configuration.
        
        Returns:
            AppConfig instance with application settings
        """
        if self._config is None:
            self._config = self._load_config()
        return self._config
    
    def _load_config(self) -> AppConfig:
        """
        Load configuration from file or return defaults.
        
        Returns:
            AppConfig instance
        """
        # Try to load from file if it exists
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f) or {}
                
                # Extract app-specific configuration
                app_data = config_data.get('app', {})
                
                # Extract database configuration
                db_data = config_data.get('database', {})
                database_config = DatabaseConfig(
                    path=db_data.get('path', DatabaseConfig.path),
                    auto_create=db_data.get('auto_create', DatabaseConfig.auto_create)
                )
                
                # Extract notification configuration
                notifications_data = config_data.get('notifications', {})
                telegram_data = notifications_data.get('telegram', {})
                telegram_config = TelegramConfig(
                    enabled=telegram_data.get('enabled', TelegramConfig.enabled),
                    bot_token=telegram_data.get('bot_token', TelegramConfig.bot_token),
                    chat_id=telegram_data.get('chat_id', TelegramConfig.chat_id),
                    timeout_seconds=telegram_data.get('timeout_seconds', TelegramConfig.timeout_seconds),
                    retry_attempts=telegram_data.get('retry_attempts', TelegramConfig.retry_attempts)
                )
                notification_config = NotificationConfig(telegram=telegram_config)
                
                return AppConfig(
                    name=app_data.get('name', AppConfig.name),
                    version=app_data.get('version', AppConfig.version),
                    description=app_data.get('description', AppConfig.description),
                    author=app_data.get('author', AppConfig.author),
                    database=database_config,
                    notifications=notification_config
                )
            except Exception:
                # If loading fails, return defaults
                pass
        
        # Return default configuration
        return AppConfig()
    
    def reload_config(self) -> AppConfig:
        """
        Reload configuration from file.
        
        Returns:
            Updated AppConfig instance
        """
        self._config = None
        return self.get_config()
    
    def get_telegram_config(self) -> TelegramConfig:
        """
        Get Telegram notification configuration.
        
        Returns:
            TelegramConfig instance
        """
        return self.get_config().notifications.telegram


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """
    Get the global configuration manager instance.
    
    Returns:
        ConfigManager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_app_config() -> AppConfig:
    """
    Get the application configuration.
    
    Returns:
        AppConfig instance
    """
    return get_config_manager().get_config()