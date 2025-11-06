"""Command pattern implementation for the CLI system."""

from typing import Dict, List, Optional
from .commands.base import BaseCommand
from .commands.version import VersionCommand
from .commands.db_info import DbInfoCommand
from .commands.notify_test import NotifyTestCommand
from .commands.youtube import YouTubeCommand
from .commands.llm import LLMCommand
from .commands.tts import TTSCommand
from .commands.summary import SummaryCommand
from src.time_reclamation.infrastructure import get_logger


class CommandRegistry:
    """Registry for managing available commands."""
    
    def __init__(self):
        """Initialize the command registry."""
        self._commands: Dict[str, BaseCommand] = {}
        self._aliases: Dict[str, str] = {}
        self.logger = get_logger()
        
        # Register default commands
        self._register_default_commands()
    
    def _register_default_commands(self) -> None:
        """Register the default set of commands."""
        self.register_command(VersionCommand())
        self.register_command(DbInfoCommand())
        self.register_command(NotifyTestCommand())
        self.register_command(YouTubeCommand())
        self.register_command(LLMCommand())
        self.register_command(TTSCommand())
        self.register_command(SummaryCommand())
    
    def register_command(self, command: BaseCommand) -> None:
        """
        Register a command in the registry.
        
        Args:
            command: Command instance to register
        """
        # Register the main command name
        self._commands[command.name] = command
        
        # Register aliases
        for alias in command.aliases:
            self._aliases[alias] = command.name
        
        self.logger.debug(f"Registered command: {command.name}")
    
    def get_command(self, name: str) -> Optional[BaseCommand]:
        """
        Get a command by name or alias.
        
        Args:
            name: Command name or alias
            
        Returns:
            Command instance if found, None otherwise
        """
        # Check if it's an alias first
        if name in self._aliases:
            name = self._aliases[name]
        
        return self._commands.get(name)
    
    def get_all_commands(self) -> Dict[str, BaseCommand]:
        """
        Get all registered commands.
        
        Returns:
            Dictionary of command name to command instance
        """
        return self._commands.copy()
    
    def list_command_names(self) -> List[str]:
        """
        Get a list of all command names.
        
        Returns:
            List of command names
        """
        return list(self._commands.keys())
    
    def command_exists(self, name: str) -> bool:
        """
        Check if a command exists.
        
        Args:
            name: Command name or alias
            
        Returns:
            True if command exists, False otherwise
        """
        return name in self._commands or name in self._aliases


class CommandInvoker:
    """Invoker class for executing commands using the command pattern."""
    
    def __init__(self, registry: Optional[CommandRegistry] = None):
        """
        Initialize the command invoker.
        
        Args:
            registry: Command registry to use (creates new one if None)
        """
        self.registry = registry or CommandRegistry()
        self.logger = get_logger()
    
    def execute_command(self, command_name: str, args: List[str]) -> int:
        """
        Execute a command by name.
        
        Args:
            command_name: Name of the command to execute
            args: Command arguments
            
        Returns:
            Exit code from command execution
        """
        # Get the command
        command = self.registry.get_command(command_name)
        
        if command is None:
            return self._handle_unknown_command(command_name)
        
        try:
            # Validate arguments
            if not command.validate_args(args):
                self.logger.error(f"Invalid arguments for command '{command_name}'")
                command.show_help()
                return 1
            
            # Execute the command
            self.logger.debug(f"Executing command: {command_name}")
            return command.execute(args)
            
        except Exception as e:
            self.logger.error(f"Error executing command '{command_name}': {str(e)}")
            return 1
    
    def _handle_unknown_command(self, command_name: str) -> int:
        """
        Handle unknown command errors.
        
        Args:
            command_name: The unknown command name
            
        Returns:
            Error exit code
        """
        self.logger.error(f"Unknown command: '{command_name}'")
        
        # Show available commands
        available_commands = self.registry.list_command_names()
        if available_commands:
            self.logger.info("Available commands:")
            for cmd_name in available_commands:
                command = self.registry.get_command(cmd_name)
                if command:
                    self.logger.print_command(cmd_name, command.description)
        
        self.logger.info("\nUse '--help' for more information.")
        return 1
    
    def list_commands(self) -> None:
        """List all available commands with descriptions."""
        commands = self.registry.get_all_commands()
        
        if not commands:
            self.logger.info("No commands available.")
            return
        
        self.logger.print_header("Available Commands")
        
        for name, command in commands.items():
            self.logger.print_command(name, command.description)
            
            # Show aliases if any
            if command.aliases:
                aliases_str = ", ".join(command.aliases)
                self.logger.print_bullet(f"Aliases: {aliases_str}", indent=4)
    
    def get_command_help(self, command_name: str) -> int:
        """
        Show help for a specific command.
        
        Args:
            command_name: Name of the command
            
        Returns:
            Exit code
        """
        command = self.registry.get_command(command_name)
        
        if command is None:
            return self._handle_unknown_command(command_name)
        
        command.show_help()
        return 0