"""CLI Manager - Main entry point for command line interface."""

import sys
from typing import List, Optional
from .command_pattern import CommandInvoker, CommandRegistry
from ...core.logging import get_logger
from ...config.manager import get_app_config


class CLIManager:
    """Main CLI manager that handles command line parsing and execution."""
    
    def __init__(self, debug: bool = False):
        """
        Initialize the CLI manager.
        
        Args:
            debug: Enable debug logging
        """
        self.logger = get_logger()
        self.invoker = CommandInvoker()
        
        if debug:
            self.logger.set_level("DEBUG")
            self.logger.debug("Debug mode enabled")
    
    def run(self, args: Optional[List[str]] = None) -> int:
        """
        Run the CLI with the given arguments.
        
        Args:
            args: Command line arguments (uses sys.argv if None)
            
        Returns:
            Exit code
        """
        if args is None:
            args = sys.argv[1:]  # Skip script name
        
        # Handle empty arguments
        if not args:
            return self._show_default_help()
        
        # Parse arguments
        command_name, command_args = self._parse_args(args)
        
        # Handle global flags
        if self._handle_global_flags(command_name, command_args):
            return 0
        
        # Execute the command
        return self.invoker.execute_command(command_name, command_args)
    
    def _parse_args(self, args: List[str]) -> tuple[str, List[str]]:
        """
        Parse command line arguments.
        
        Args:
            args: Raw command line arguments
            
        Returns:
            Tuple of (command_name, command_arguments)
        """
        if not args:
            return "help", []
        
        command_name = args[0].lower()
        command_args = args[1:] if len(args) > 1 else []
        
        return command_name, command_args
    
    def _handle_global_flags(self, command_name: str, command_args: List[str]) -> bool:
        """
        Handle global flags that apply to the entire application.
        
        Args:
            command_name: The command name
            command_args: Command arguments
            
        Returns:
            True if a global flag was handled, False otherwise
        """
        # Handle version flag
        if command_name in ["--version", "-v", "version"]:
            self._show_version()
            return True
        
        # Handle global help flags
        if command_name in ["--help", "-h"] or (not command_name and "--help" in command_args):
            return self._show_default_help() == 0
        
        # Handle debug flag
        if "--debug" in command_args:
            self.logger.set_level("DEBUG")
            self.logger.debug("Debug mode enabled via --debug flag")
            # Remove debug flag from args
            command_args.remove("--debug")
        
        return False
    
    def _show_default_help(self) -> int:
        """
        Show default help when no command is provided.
        
        Returns:
            Exit code
        """
        # Get app config for display
        app_config = get_app_config()
        
        # Show basic help information
        self.logger.print_header(app_config.name, width=60)
        self.logger.print_section("DESCRIPTION")
        self.logger.print_bullet(app_config.description)
        
        self.logger.print_section("USAGE")
        self.logger.print_bullet("python -m time_reclamation <command> [options]")
        self.logger.print_bullet("python main.py <command> [options]")
        
        self.logger.print_section("AVAILABLE COMMANDS")
        self.invoker.list_commands()
        
        self.logger.print_section("GETTING HELP")
        self.logger.print_bullet("For more information about a specific command, use:")
        self.logger.print_example("python main.py <command> --help")
        
        return 0
    
    def _show_version(self) -> None:
        """Show application version information."""
        app_config = get_app_config()
        self.logger.print_header(app_config.name)
        self.logger.info(f"Version: {app_config.version}")
        self.logger.info(f"Description: {app_config.description}")
        self.logger.info(f"Author: {app_config.author}")
    
    def add_command(self, command) -> None:
        """
        Add a custom command to the CLI.
        
        Args:
            command: Command instance to add
        """
        self.invoker.registry.register_command(command)
        self.logger.debug(f"Added custom command: {command.name}")
    
    def list_commands(self) -> None:
        """List all available commands."""
        self.invoker.list_commands()
    
    def get_command_help(self, command_name: str) -> int:
        """
        Get help for a specific command.
        
        Args:
            command_name: Name of the command
            
        Returns:
            Exit code
        """
        return self.invoker.get_command_help(command_name)


def create_cli(debug: bool = False) -> CLIManager:
    """
    Factory function to create a CLI manager instance.
    
    Args:
        debug: Enable debug logging
        
    Returns:
        CLIManager instance
    """
    return CLIManager(debug=debug)


def main(args: Optional[List[str]] = None) -> int:
    """
    Main entry point for the CLI application.
    
    Args:
        args: Command line arguments
        
    Returns:
        Exit code
    """
    try:
        cli = create_cli()
        return cli.run(args)
    except KeyboardInterrupt:
        logger = get_logger()
        logger.info("\nOperation cancelled by user.")
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        logger = get_logger()
        logger.error(f"Unexpected error: {str(e)}")
        logger.debug("Use --debug flag for more detailed error information")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)