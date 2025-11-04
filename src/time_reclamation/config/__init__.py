"""Configuration management for Time Reclamation App."""

from .manager import get_config_manager, AppConfig

__all__ = [
    "get_config_manager",
    "AppConfig",
]