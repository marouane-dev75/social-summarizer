#!/usr/bin/env python3
"""
Main entry point for the Time Reclamation App.

This script provides the primary interface for running the time reclamation
application with various commands for content curation and summarization.
"""

import sys
import os

# Add the current directory to Python path to ensure imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.time_reclamation import main as cli_main


def main():
    """
    Main entry point for the application.
    
    This function serves as the primary entry point and delegates
    to the CLI manager for command processing.
    """
    try:
        # Run the CLI application
        exit_code = cli_main()
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(130)  # Standard exit code for SIGINT
        
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        print("Please check your installation and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()