"""Database info command implementation."""

from typing import List
from .base import BaseCommand
from src.time_reclamation.infrastructure.database import get_database_manager


class DbInfoCommand(BaseCommand):
    """Command to display database status and information."""
    
    @property
    def name(self) -> str:
        """Return the command name."""
        return "db-info"
    
    @property
    def description(self) -> str:
        """Return the command description."""
        return "Display database status and file size information"
    
    @property
    def aliases(self) -> List[str]:
        """Return command aliases."""
        return ["database-info", "db-status"]
    
    @property
    def usage(self) -> str:
        """Return command usage string."""
        return f"python -m time_reclamation {self.name}"
    
    def execute(self, args: List[str]) -> int:
        """
        Execute the db-info command.
        
        Args:
            args: Command line arguments
            
        Returns:
            Exit code (0 for success)
        """
        try:
            # Get database manager
            db_manager = get_database_manager()
            
            # Get database information
            db_info = db_manager.get_database_info()
            
            # If database doesn't exist, create it automatically
            if not db_info['exists']:
                self.logger.info("Database not found. Creating database...")
                if db_manager.initialize_database():
                    self.logger.info("✓ Database created successfully")
                    # Refresh database info after creation
                    db_info = db_manager.get_database_info()
                else:
                    self.logger.error("✗ Failed to create database")
            
            # Display header
            self.logger.print_header("Database Information")
            
            # Display basic information
            self.logger.print_section("LOCATION")
            self.logger.print_bullet(f"Path: {db_info['path']}")
            
            self.logger.print_section("STATUS")
            if db_info['exists']:
                self.logger.print_bullet("✓ Database file exists")
                self.logger.print_bullet(f"✓ File size: {db_info['size_mb']} MB")
                
                if db_info['readable']:
                    self.logger.print_bullet("✓ Database is readable")
                else:
                    self.logger.print_bullet("✗ Database is not readable")
                
                if db_info['writable']:
                    self.logger.print_bullet("✓ Database is writable")
                else:
                    self.logger.print_bullet("✗ Database is not writable")
            else:
                self.logger.print_bullet("✗ Database file does not exist")
                self.logger.print_bullet("✗ Failed to create database automatically")
            
            # Show additional info if database exists
            if db_info['exists'] and db_info['readable']:
                self._show_detailed_info(db_manager)
            
            return self.handle_success()
            
        except Exception as e:
            return self.handle_error(f"Failed to retrieve database information: {str(e)}")
    
    def _show_detailed_info(self, db_manager) -> None:
        """
        Show detailed database information.
        
        Args:
            db_manager: Database manager instance
        """
        try:
            self.logger.print_section("DETAILS")
            
            # Try to get table count (basic implementation)
            with db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) as table_count 
                    FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
                table_count = cursor.fetchone()[0]
                self.logger.print_bullet(f"Tables: {table_count}")
                
        except Exception as e:
            self.logger.debug(f"Could not retrieve detailed info: {str(e)}")
            self.logger.print_bullet("Detailed information unavailable")
    
    def validate_args(self, args: List[str]) -> bool:
        """
        Validate command arguments.
        
        Args:
            args: Command line arguments
            
        Returns:
            True (db-info command doesn't require arguments)
        """
        return True
    
    def show_help(self) -> None:
        """Show help information for this command."""
        super().show_help()
        
        self.logger.print_section("EXAMPLES")
        self.logger.print_bullet("python main.py db-info")
        self.logger.print_bullet("python -m time_reclamation database-info")
        
        self.logger.print_section("NOTES")
        self.logger.print_bullet("This command shows the current database file size and status")
        self.logger.print_bullet("If the database doesn't exist, it will be created automatically when needed")