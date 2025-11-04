"""Time Reclamation App - Reclaim time wasted on social media through intelligent curation."""

# Main interface (imported last to avoid circular imports)
from .interfaces.cli import main

__all__ = [
    # Main interface
    "main",
]