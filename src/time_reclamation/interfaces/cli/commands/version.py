"""Version command implementation."""

from typing import List
from .base import BaseCommand
from src.time_reclamation.config import get_app_config


class VersionCommand(BaseCommand):
    """Command to display application version information."""
    
    @property
    def name(self) -> str:
        """Return the command name."""
        return "version"
    
    @property
    def description(self) -> str:
        """Return the command description."""
        return "Display application version and information"
    
    @property
    def aliases(self) -> List[str]:
        """Return command aliases."""
        return ["--version", "-v"]
    
    def execute(self, args: List[str]) -> int:
        """
        Execute the version command.
        
        Args:
            args: Command line arguments
            
        Returns:
            Exit code (0 for success)
        """
        try:
            # Get application configuration
            app_config = get_app_config()
            
            # Display version information
            self.logger.print_header(app_config.name)
            self.logger.info(f"Version: {app_config.version}")
            self.logger.info(f"Description: {app_config.description}")
            self.logger.info(f"Author: {app_config.author}")
            
            return self.handle_success()
            
        except Exception as e:
            return self.handle_error(f"Failed to retrieve version information: {str(e)}")
    
    def validate_args(self, args: List[str]) -> bool:
        """
        Validate command arguments.
        
        Args:
            args: Command line arguments
            
        Returns:
            True (version command doesn't require arguments)
        """
        return True