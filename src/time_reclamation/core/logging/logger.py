"""Logging system for Time Reclamation App."""

import logging
import sys
import os
import yaml
from typing import Optional
from enum import Enum


class Colors:
    """ANSI color codes for console output."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Standard colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ConsoleLogger:
    """Enhanced console logger with formatting and colors."""
    
    def __init__(self, name: str = "TimeReclamation", use_colors: bool = True):
        """
        Initialize the console logger.
        
        Args:
            name: Logger name
            use_colors: Whether to use colors in output
        """
        self.name = name
        self.use_colors = use_colors and sys.stdout.isatty()
        self.logger = logging.getLogger(name)
        
        # Set up basic logging configuration if not already configured
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def debug(self, message: str) -> None:
        """Log debug message."""
        self.logger.debug(message)
    
    def info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)
    
    def warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(message)
    
    def error(self, message: str) -> None:
        """Log error message."""
        self.logger.error(message)
    
    def critical(self, message: str) -> None:
        """Log critical message."""
        self.logger.critical(message)
    
    def success(self, message: str) -> None:
        """Log success message (info level with green color)."""
        if self.use_colors:
            colored_message = f"{Colors.GREEN}{message}{Colors.RESET}"
            self.logger.info(colored_message)
        else:
            self.logger.info(f"SUCCESS: {message}")
    
    def print_header(self, title: str, width: int = 50) -> None:
        """Print a formatted header."""
        border = "=" * width
        if self.use_colors:
            print(f"{Colors.BOLD}{Colors.CYAN}{border}{Colors.RESET}")
            print(f"{Colors.BOLD}{Colors.CYAN}{title.center(width)}{Colors.RESET}")
            print(f"{Colors.BOLD}{Colors.CYAN}{border}{Colors.RESET}")
        else:
            print(border)
            print(title.center(width))
            print(border)
    
    def print_section(self, title: str) -> None:
        """Print a section header."""
        if self.use_colors:
            print(f"\n{Colors.BOLD}{Colors.YELLOW}{title}:{Colors.RESET}")
        else:
            print(f"\n{title}:")
    
    def print_bullet(self, text: str, indent: int = 2) -> None:
        """Print a bullet point."""
        spaces = " " * indent
        if self.use_colors:
            print(f"{spaces}{Colors.BRIGHT_BLUE}•{Colors.RESET} {text}")
        else:
            print(f"{spaces}• {text}")
    
    def print_command(self, command: str, description: str) -> None:
        """Print a command with its description."""
        if self.use_colors:
            print(f"  {Colors.BOLD}{Colors.GREEN}{command:<15}{Colors.RESET} {description}")
        else:
            print(f"  {command:<15} {description}")
    
    def print_example(self, example: str) -> None:
        """Print an example command."""
        if self.use_colors:
            print(f"    {Colors.BRIGHT_BLACK}{example}{Colors.RESET}")
        else:
            print(f"    {example}")
    
    def set_level(self, level: str) -> None:
        """Set the logging level."""
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        
        if level.upper() in level_map:
            self.logger.setLevel(level_map[level.upper()])
        else:
            self.warning(f"Unknown log level: {level}")


# Global logger instance
_logger: Optional[ConsoleLogger] = None


def get_logger(name: str = "TimeReclamation") -> ConsoleLogger:
    """
    Get the global logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        ConsoleLogger instance
    """
    global _logger
    if _logger is None:
        _logger = ConsoleLogger(name)
        # Set logging level from configuration
        try:
            from src.time_reclamation.core import get_config_manager
            config_manager = get_config_manager()
            
            # Try to load logging config from YAML if available
            if os.path.exists(config_manager.config_path):
                with open(config_manager.config_path, 'r', encoding='utf-8') as f:
                    yaml_config = yaml.safe_load(f) or {}
                    logging_config = yaml_config.get('logging', {})
                    log_level = logging_config.get('level', 'INFO')
                    _logger.set_level(log_level)
        except Exception:
            # If config loading fails, use default INFO level
            _logger.set_level('INFO')
    
    return _logger