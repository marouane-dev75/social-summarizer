"""Database manager for SQLite operations."""

import os
import sqlite3
from pathlib import Path
from typing import Optional
from contextlib import contextmanager
from src.time_reclamation.config import get_app_config
from src.time_reclamation.core import get_logger


class DatabaseManager:
    """Manages SQLite database operations for state persistence."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the database manager.
        
        Args:
            db_path: Path to the database file (uses config if None)
        """
        self.logger = get_logger()
        self.config = get_app_config()
        self.db_path = db_path or self.config.database.path
        self._ensure_database_directory()
    
    def _ensure_database_directory(self) -> None:
        """Ensure the database directory exists."""
        db_dir = Path(self.db_path).parent
        if not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created database directory: {db_dir}")
    
    @contextmanager
    def get_connection(self):
        """
        Get a database connection using context manager.
        
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            yield conn
        except sqlite3.Error as e:
            self.logger.error(f"Database error: {str(e)}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def get_database_size_mb(self) -> float:
        """
        Get the database file size in megabytes.
        
        Returns:
            Database file size in MB, or 0.0 if file doesn't exist
        """
        try:
            if not os.path.exists(self.db_path):
                return 0.0
            
            size_bytes = os.path.getsize(self.db_path)
            size_mb = size_bytes / (1024 * 1024)  # Convert bytes to MB
            return round(size_mb, 2)
            
        except OSError as e:
            self.logger.error(f"Error getting database size: {str(e)}")
            return 0.0
    
    def database_exists(self) -> bool:
        """
        Check if the database file exists.
        
        Returns:
            True if database file exists, False otherwise
        """
        return os.path.exists(self.db_path)
    
    def initialize_database(self) -> bool:
        """
        Initialize the database with basic structure.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            if not self.config.database.auto_create:
                self.logger.debug("Database auto-creation is disabled")
                return False
            
            with self.get_connection() as conn:
                # Create a basic metadata table for future use
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS app_metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Insert initial metadata
                conn.execute("""
                    INSERT OR IGNORE INTO app_metadata (key, value) 
                    VALUES ('database_version', '1.0')
                """)
                
                conn.commit()
                self.logger.debug("Database initialized successfully")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {str(e)}")
            return False
    
    def get_database_info(self) -> dict:
        """
        Get comprehensive database information.
        
        Returns:
            Dictionary containing database information
        """
        info = {
            'path': self.db_path,
            'exists': self.database_exists(),
            'size_mb': self.get_database_size_mb(),
            'readable': False,
            'writable': False
        }
        
        if info['exists']:
            try:
                # Test read access
                with self.get_connection() as conn:
                    conn.execute("SELECT 1")
                    info['readable'] = True
                
                # Test write access
                if os.access(self.db_path, os.W_OK):
                    info['writable'] = True
                    
            except Exception as e:
                self.logger.debug(f"Database access test failed: {str(e)}")
        
        return info


# Global database manager instance
_database_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """
    Get the global database manager instance.
    
    Returns:
        DatabaseManager instance
    """
    global _database_manager
    if _database_manager is None:
        _database_manager = DatabaseManager()
    return _database_manager