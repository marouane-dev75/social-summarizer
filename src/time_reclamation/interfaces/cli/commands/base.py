"""Base command class for the command pattern implementation."""

import traceback
from abc import ABC, abstractmethod
from typing import List
from src.time_reclamation.core import get_logger


class BaseCommand(ABC):
    """Abstract base class for all commands."""
    
    def __init__(self):
        """Initialize the base command."""
        self.logger = get_logger()
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the command name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Return the command description."""
        pass
    
    @property
    def aliases(self) -> List[str]:
        """Return command aliases (optional)."""
        return []
    
    @property
    def usage(self) -> str:
        """Return command usage string."""
        return f"python -m time_reclamation {self.name}"
    
    @abstractmethod
    def execute(self, args: List[str]) -> int:
        """
        Execute the command.
        
        Args:
            args: Command line arguments
            
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        pass
    
    def validate_args(self, args: List[str]) -> bool:
        """
        Validate command arguments.
        
        Args:
            args: Command line arguments
            
        Returns:
            True if arguments are valid, False otherwise
        """
        return True
    
    def show_help(self) -> None:
        """Show help information for this command."""
        self.logger.print_header(f"{self.name.upper()} Command Help")
        
        self.logger.print_section("DESCRIPTION")
        self.logger.print_bullet(self.description)
        
        self.logger.print_section("USAGE")
        self.logger.print_bullet(self.usage)
        
        if self.aliases:
            self.logger.print_section("ALIASES")
            for alias in self.aliases:
                self.logger.print_bullet(alias)
    
    def handle_error(self, error_message: str, exit_code: int = 1) -> int:
        """
        Handle command errors consistently.
        
        Args:
            error_message: Error message to display
            exit_code: Exit code to return
            
        Returns:
            Exit code
        """
        self.logger.error(error_message)
        self.logger.error(f"Stack trace:\n{traceback.format_exc()}")
        return exit_code
    
    def handle_success(self, success_message: str = "") -> int:
        """
        Handle command success consistently.
        
        Args:
            success_message: Optional success message to display
            
        Returns:
            Success exit code (0)
        """
        if success_message:
            self.logger.success(success_message)
        return 0