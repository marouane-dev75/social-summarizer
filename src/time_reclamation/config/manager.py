"""Configuration manager for Time Reclamation App."""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import os
import yaml
from pathlib import Path


@dataclass
class DatabaseConfig:
    """Database configuration data class."""
    path: str = "cache_data/state.db"
    auto_create: bool = True


@dataclass
class ProviderInstanceConfig:
    """Provider instance configuration data class."""
    name: str = ""
    type: str = ""
    enabled: bool = True
    config: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize config dictionary."""
        if self.config is None:
            self.config = {}


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
    providers: List[ProviderInstanceConfig] = None
    
    def __post_init__(self):
        """Initialize providers list."""
        if self.providers is None:
            self.providers = []


@dataclass
class LLMConfig:
    """LLM configuration data class."""
    providers: List[ProviderInstanceConfig] = None
    
    def __post_init__(self):
        """Initialize providers list."""
        if self.providers is None:
            self.providers = []


@dataclass
class AppConfig:
    """Application configuration data class."""
    name: str = "Time Reclamation App"
    version: str = "1.0.0"
    description: str = "Reclaim time wasted on social media by getting curated summaries instead of endless scrolling"
    author: str = "Time Reclamation Team"
    database: DatabaseConfig = None
    notifications: NotificationConfig = None
    llm: LLMConfig = None
    platforms: PlatformsConfig = None
    
    def __post_init__(self):
        """Initialize nested configurations."""
        if self.database is None:
            self.database = DatabaseConfig()
        if self.notifications is None:
            self.notifications = NotificationConfig()
        if self.llm is None:
            self.llm = LLMConfig()
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
        providers_data = notifications_data.get('providers', [])
        
        provider_instances = []
        instance_names = set()
        
        for provider_data in providers_data:
            if isinstance(provider_data, dict):
                instance_config = ProviderInstanceConfig(
                    name=provider_data.get('name', ''),
                    type=provider_data.get('type', ''),
                    enabled=provider_data.get('enabled', True),
                    config=provider_data.get('config', {})
                )
                
                # Validate instance configuration
                validation_errors = self._validate_provider_instance(instance_config, instance_names)
                if validation_errors:
                    # Log validation errors but continue loading other instances
                    for error in validation_errors:
                        print(f"Configuration validation error: {error}")
                    continue
                
                instance_names.add(instance_config.name)
                provider_instances.append(instance_config)
        
        notification_config = NotificationConfig(providers=provider_instances)
        
        # Extract LLM configuration
        llm_data = merged_config.get('llm', {})
        llm_providers_data = llm_data.get('providers', [])
        
        llm_provider_instances = []
        llm_instance_names = set()
        
        for provider_data in llm_providers_data:
            if isinstance(provider_data, dict):
                instance_config = ProviderInstanceConfig(
                    name=provider_data.get('name', ''),
                    type=provider_data.get('type', ''),
                    enabled=provider_data.get('enabled', True),
                    config=provider_data.get('config', {})
                )
                
                # Validate LLM instance configuration
                validation_errors = self._validate_llm_provider_instance(instance_config, llm_instance_names)
                if validation_errors:
                    # Log validation errors but continue loading other instances
                    for error in validation_errors:
                        print(f"LLM configuration validation error: {error}")
                    continue
                
                llm_instance_names.add(instance_config.name)
                llm_provider_instances.append(instance_config)
        
        llm_config = LLMConfig(providers=llm_provider_instances)
        
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
            llm=llm_config,
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
    
    def get_provider_instances(self) -> List[ProviderInstanceConfig]:
        """
        Get all provider instances configuration.
        
        Returns:
            List of ProviderInstanceConfig instances
        """
        return self.get_config().notifications.providers
    
    def get_provider_instance(self, name: str) -> Optional[ProviderInstanceConfig]:
        """
        Get a specific provider instance by name.
        
        Args:
            name: Name of the provider instance
            
        Returns:
            ProviderInstanceConfig instance or None if not found
        """
        for provider in self.get_provider_instances():
            if provider.name == name:
                return provider
        return None
    
    def _validate_provider_instance(self, instance: ProviderInstanceConfig, existing_names: set) -> List[str]:
        """
        Validate a provider instance configuration.
        
        Args:
            instance: Provider instance configuration to validate
            existing_names: Set of already processed instance names
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Validate instance name
        if not instance.name or not instance.name.strip():
            errors.append("Provider instance name cannot be empty")
        elif instance.name in existing_names:
            errors.append(f"Duplicate provider instance name: '{instance.name}'")
        elif not instance.name.replace('_', '').replace('-', '').isalnum():
            errors.append(f"Provider instance name '{instance.name}' contains invalid characters. Use only letters, numbers, hyphens, and underscores")
        
        # Validate provider type
        if not instance.type or not instance.type.strip():
            errors.append(f"Provider instance '{instance.name}' must specify a type")
        elif instance.type.lower() not in ['telegram']:  # Add more types as they're implemented
            errors.append(f"Unknown provider type '{instance.type}' for instance '{instance.name}'. Supported types: telegram")
        
        # Validate type-specific configuration
        if instance.type.lower() == 'telegram' and instance.enabled:
            telegram_errors = self._validate_telegram_config(instance.name, instance.config)
            errors.extend(telegram_errors)
        
        return errors
    
    def _validate_telegram_config(self, instance_name: str, config: Dict[str, Any]) -> List[str]:
        """
        Validate Telegram-specific configuration.
        
        Args:
            instance_name: Name of the instance being validated
            config: Telegram configuration dictionary
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check required fields
        bot_token = config.get('bot_token', '')
        chat_id = config.get('chat_id', '')
        
        if not bot_token or bot_token == 'YOUR_BOT_TOKEN_HERE' or bot_token == 'YOUR_WORK_BOT_TOKEN_HERE' or bot_token == 'YOUR_PERSONAL_BOT_TOKEN_HERE':
            errors.append(f"Telegram instance '{instance_name}' requires a valid bot_token")
        
        if not chat_id or chat_id == 'YOUR_CHAT_ID_HERE' or chat_id == 'YOUR_WORK_CHAT_ID_HERE' or chat_id == 'YOUR_PERSONAL_CHAT_ID_HERE':
            errors.append(f"Telegram instance '{instance_name}' requires a valid chat_id")
        
        # Validate bot token format (basic check)
        if bot_token and bot_token not in ['YOUR_BOT_TOKEN_HERE', 'YOUR_WORK_BOT_TOKEN_HERE', 'YOUR_PERSONAL_BOT_TOKEN_HERE']:
            parts = bot_token.split(':')
            if len(parts) != 2 or not parts[0].isdigit() or len(parts[1]) < 10:
                errors.append(f"Telegram instance '{instance_name}' has invalid bot_token format")
        
        # Validate numeric settings
        timeout = config.get('timeout_seconds', 30)
        if not isinstance(timeout, int) or timeout <= 0:
            errors.append(f"Telegram instance '{instance_name}' timeout_seconds must be a positive integer")
        
        retry_attempts = config.get('retry_attempts', 3)
        if not isinstance(retry_attempts, int) or retry_attempts < 0:
            errors.append(f"Telegram instance '{instance_name}' retry_attempts must be a non-negative integer")
        
        return errors
    
    def _validate_llm_provider_instance(self, instance: ProviderInstanceConfig, existing_names: set) -> List[str]:
        """
        Validate an LLM provider instance configuration.
        
        Args:
            instance: LLM provider instance configuration to validate
            existing_names: Set of already processed instance names
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Validate instance name
        if not instance.name or not instance.name.strip():
            errors.append("LLM provider instance name cannot be empty")
        elif instance.name in existing_names:
            errors.append(f"Duplicate LLM provider instance name: '{instance.name}'")
        elif not instance.name.replace('_', '').replace('-', '').isalnum():
            errors.append(f"LLM provider instance name '{instance.name}' contains invalid characters. Use only letters, numbers, hyphens, and underscores")
        
        # Validate provider type
        if not instance.type or not instance.type.strip():
            errors.append(f"LLM provider instance '{instance.name}' must specify a type")
        elif instance.type.lower() not in ['llamacpp']:  # Add more types as they're implemented
            errors.append(f"Unknown LLM provider type '{instance.type}' for instance '{instance.name}'. Supported types: llamacpp")
        
        # Validate type-specific configuration
        if instance.type.lower() == 'llamacpp' and instance.enabled:
            llamacpp_errors = self._validate_llamacpp_config(instance.name, instance.config)
            errors.extend(llamacpp_errors)
        
        return errors
    
    def _validate_llamacpp_config(self, instance_name: str, config: Dict[str, Any]) -> List[str]:
        """
        Validate LlamaCpp-specific configuration.
        
        Args:
            instance_name: Name of the instance being validated
            config: LlamaCpp configuration dictionary
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check required fields
        model_path = config.get('model_path', '')
        
        if not model_path or model_path == '/path/to/your/model.gguf' or model_path == '/path/to/code-model.gguf':
            errors.append(f"LlamaCpp instance '{instance_name}' requires a valid model_path")
        elif not model_path.lower().endswith('.gguf'):
            errors.append(f"LlamaCpp instance '{instance_name}' model_path must be a GGUF file (.gguf extension)")
        
        # Validate numeric settings
        context_size = config.get('context_size', 4096)
        if not isinstance(context_size, int) or context_size <= 0:
            errors.append(f"LlamaCpp instance '{instance_name}' context_size must be a positive integer")
        
        gpu_layers = config.get('gpu_layers', 0)
        if not isinstance(gpu_layers, int) or gpu_layers < -1:
            errors.append(f"LlamaCpp instance '{instance_name}' gpu_layers must be -1 or a non-negative integer")
        
        # Validate generation config
        generation_config = config.get('generation_config', {})
        if isinstance(generation_config, dict):
            max_tokens = generation_config.get('max_tokens', 8000)
            if not isinstance(max_tokens, int) or max_tokens <= 0:
                errors.append(f"LlamaCpp instance '{instance_name}' generation_config.max_tokens must be a positive integer")
            
            temperature = generation_config.get('temperature', 0.7)
            if not isinstance(temperature, (int, float)) or temperature < 0 or temperature > 2:
                errors.append(f"LlamaCpp instance '{instance_name}' generation_config.temperature must be between 0 and 2")
        
        return errors
    
    def get_llm_provider_instances(self) -> List[ProviderInstanceConfig]:
        """
        Get all LLM provider instances configuration.
        
        Returns:
            List of ProviderInstanceConfig instances for LLM providers
        """
        return self.get_config().llm.providers
    
    def get_llm_provider_instance(self, name: str) -> Optional[ProviderInstanceConfig]:
        """
        Get a specific LLM provider instance by name.
        
        Args:
            name: Name of the LLM provider instance
            
        Returns:
            ProviderInstanceConfig instance or None if not found
        """
        for provider in self.get_llm_provider_instances():
            if provider.name == name:
                return provider
        return None


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