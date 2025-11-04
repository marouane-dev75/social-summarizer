"""Configuration manager for Time Reclamation App."""

from dataclasses import dataclass
from typing import Optional, Dict, Any
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
class YouTubeChannelConfig:
    """YouTube channel configuration data class."""
    name: str = ""
    scrap: bool = False
    url: str = ""
    max_videos: int = 10
    language: str = "en"
    cache_folder: str = "cache_data/youtube_transcripts/default"


@dataclass
class YouTubePlatformConfig:
    """YouTube platform configuration data class."""
    enabled: bool = True
    channels: list = None
    
    def __post_init__(self):
        """Initialize channels list."""
        if self.channels is None:
            self.channels = []


@dataclass
class PlatformsConfig:
    """Platforms configuration data class."""
    youtube: YouTubePlatformConfig = None
    reddit: dict = None
    twitter: dict = None
    
    def __post_init__(self):
        """Initialize platform configurations."""
        if self.youtube is None:
            self.youtube = YouTubePlatformConfig()
        if self.reddit is None:
            self.reddit = {"enabled": True}
        if self.twitter is None:
            self.twitter = {"enabled": True}


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
    platforms: PlatformsConfig = None
    
    def __post_init__(self):
        """Initialize nested configurations."""
        if self.database is None:
            self.database = DatabaseConfig()
        if self.notifications is None:
            self.notifications = NotificationConfig()
        if self.platforms is None:
            self.platforms = PlatformsConfig()


class ConfigManager:
    """Manages application configuration."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to configuration file (optional)
        """
        self.config_path = config_path or self._get_default_config_path()
        self.local_config_path = self._get_local_config_path()
        self._config: Optional[AppConfig] = None
    
    def _get_default_config_path(self) -> str:
        """Get the default configuration file path."""
        # Look for config.yml in the config directory
        config_dir = Path(__file__).parent
        return str(config_dir / "config.yml")
    
    def _get_local_config_path(self) -> str:
        """Get the local configuration file path for sensitive overrides."""
        config_dir = Path(__file__).parent
        return str(config_dir / "config.local.yml")
    
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
        Merges main config with local overrides if available.
        
        Returns:
            AppConfig instance
        """
        # Load main configuration
        config_data = self._load_yaml_file(self.config_path)
        
        # Load local overrides if they exist
        local_config_data = self._load_yaml_file(self.local_config_path)
        
        # Merge configurations (local overrides main)
        merged_config = self._merge_configs(config_data, local_config_data)
        
        # Extract app-specific configuration
        app_data = merged_config.get('app', {})
        
        # Extract database configuration
        db_data = merged_config.get('database', {})
        database_config = DatabaseConfig(
            path=db_data.get('path', DatabaseConfig.path),
            auto_create=db_data.get('auto_create', DatabaseConfig.auto_create)
        )
        
        # Extract notification configuration
        notifications_data = merged_config.get('notifications', {})
        telegram_data = notifications_data.get('telegram', {})
        telegram_config = TelegramConfig(
            enabled=telegram_data.get('enabled', TelegramConfig.enabled),
            bot_token=telegram_data.get('bot_token', TelegramConfig.bot_token),
            chat_id=telegram_data.get('chat_id', TelegramConfig.chat_id),
            timeout_seconds=telegram_data.get('timeout_seconds', TelegramConfig.timeout_seconds),
            retry_attempts=telegram_data.get('retry_attempts', TelegramConfig.retry_attempts)
        )
        notification_config = NotificationConfig(telegram=telegram_config)
        
        # Extract platforms configuration
        platforms_data = merged_config.get('platforms', {})
        
        # Extract YouTube configuration
        youtube_data = platforms_data.get('youtube', {})
        youtube_channels = []
        
        for channel_data in youtube_data.get('channels', []):
            if isinstance(channel_data, dict):
                youtube_channels.append(channel_data)
        
        youtube_config = YouTubePlatformConfig(
            enabled=youtube_data.get('enabled', True),
            channels=youtube_channels
        )
        
        platforms_config = PlatformsConfig(
            youtube=youtube_config,
            reddit=platforms_data.get('reddit', {"enabled": True}),
            twitter=platforms_data.get('twitter', {"enabled": True})
        )
        
        return AppConfig(
            name=app_data.get('name', AppConfig.name),
            version=app_data.get('version', AppConfig.version),
            description=app_data.get('description', AppConfig.description),
            author=app_data.get('author', AppConfig.author),
            database=database_config,
            notifications=notification_config,
            platforms=platforms_config
        )
    
    def _load_yaml_file(self, file_path: str) -> Dict[str, Any]:
        """
        Load YAML configuration from a file.
        
        Args:
            file_path: Path to the YAML file
            
        Returns:
            Dictionary with configuration data, empty dict if file doesn't exist or fails to load
        """
        if not os.path.exists(file_path):
            return {}
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception:
            # If loading fails, return empty dict
            return {}
    
    def _merge_configs(self, base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively merge two configuration dictionaries.
        Values in override_config take precedence over base_config.
        
        Args:
            base_config: Base configuration dictionary
            override_config: Override configuration dictionary
            
        Returns:
            Merged configuration dictionary
        """
        if not override_config:
            return base_config.copy()
            
        if not base_config:
            return override_config.copy()
            
        merged = base_config.copy()
        
        for key, value in override_config.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                merged[key] = self._merge_configs(merged[key], value)
            else:
                # Override the value
                merged[key] = value
                
        return merged
    
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