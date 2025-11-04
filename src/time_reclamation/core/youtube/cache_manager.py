"""YouTube transcript cache management."""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from src.time_reclamation.infrastructure import get_logger


class YouTubeCacheManager:
    """Manages caching of YouTube transcripts to the filesystem."""
    
    def __init__(self, base_cache_dir: str = "cache_data/youtube_transcripts"):
        """
        Initialize the cache manager.
        
        Args:
            base_cache_dir: Base directory for caching transcripts
        """
        self.base_cache_dir = Path(base_cache_dir)
        self.logger = get_logger()
        self._ensure_cache_directory()
    
    def _ensure_cache_directory(self) -> None:
        """Ensure the cache directory exists."""
        try:
            self.base_cache_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Cache directory ensured: {self.base_cache_dir}")
        except Exception as e:
            self.logger.error(f"Failed to create cache directory: {str(e)}")
            raise
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to be filesystem-safe.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove or replace problematic characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Limit length and remove leading/trailing spaces
        filename = filename.strip()[:200]
        
        return filename
    
    def _get_cache_path(self, channel_cache_folder: str, video_id: str, title: str) -> Path:
        """
        Get the cache file path for a video transcript.
        
        Args:
            channel_cache_folder: Channel-specific cache folder
            video_id: YouTube video ID
            title: Video title
            
        Returns:
            Path to the cache file
        """
        # Create channel-specific directory
        channel_dir = Path(channel_cache_folder)
        channel_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename with video ID and sanitized title
        sanitized_title = self._sanitize_filename(title or "untitled")
        filename = f"{video_id}_{sanitized_title}.json"
        
        return channel_dir / filename
    
    def transcript_exists(self, channel_cache_folder: str, video_id: str, title: str) -> bool:
        """
        Check if a transcript file already exists in cache.
        
        Args:
            channel_cache_folder: Channel-specific cache folder
            video_id: YouTube video ID
            title: Video title
            
        Returns:
            True if transcript file exists, False otherwise
        """
        try:
            cache_path = self._get_cache_path(channel_cache_folder, video_id, title)
            exists = cache_path.exists() and cache_path.is_file()
            
            if exists:
                self.logger.debug(f"Transcript cache file exists: {cache_path}")
            
            return exists
            
        except Exception as e:
            self.logger.error(f"Error checking transcript cache existence: {str(e)}")
            return False
    
    def save_transcript(self, transcript_data: Dict[str, Any], channel_cache_folder: str, 
                       video_id: str, title: str) -> Optional[str]:
        """
        Save transcript data to cache file.
        
        Args:
            transcript_data: Transcript data dictionary
            channel_cache_folder: Channel-specific cache folder
            video_id: YouTube video ID
            title: Video title
            
        Returns:
            Path to saved file or None if failed
        """
        try:
            cache_path = self._get_cache_path(channel_cache_folder, video_id, title)
            
            # Add cache metadata
            cache_data = {
                'cached_at': datetime.now(timezone.utc).isoformat(),
                'video_id': video_id,
                'title': title,
                'cache_path': str(cache_path),
                'transcript': transcript_data
            }
            
            # Write to file
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Transcript saved to cache: {cache_path}")
            return str(cache_path)
            
        except Exception as e:
            self.logger.error(f"Error saving transcript to cache: {str(e)}")
            return None
    
    def load_transcript(self, channel_cache_folder: str, video_id: str, title: str) -> Optional[Dict[str, Any]]:
        """
        Load transcript data from cache file.
        
        Args:
            channel_cache_folder: Channel-specific cache folder
            video_id: YouTube video ID
            title: Video title
            
        Returns:
            Transcript data dictionary or None if not found/error
        """
        try:
            cache_path = self._get_cache_path(channel_cache_folder, video_id, title)
            
            if not cache_path.exists():
                return None
            
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            self.logger.debug(f"Transcript loaded from cache: {cache_path}")
            return cache_data.get('transcript')
            
        except Exception as e:
            self.logger.error(f"Error loading transcript from cache: {str(e)}")
            return None
    
    def load_transcript_by_path(self, cache_path: str) -> Optional[Dict[str, Any]]:
        """
        Load transcript data from a specific cache file path.
        
        Args:
            cache_path: Path to the cache file
            
        Returns:
            Transcript data dictionary or None if not found/error
        """
        try:
            path = Path(cache_path)
            
            if not path.exists():
                self.logger.warning(f"Cache file not found: {cache_path}")
                return None
            
            with open(path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            self.logger.debug(f"Transcript loaded from cache path: {cache_path}")
            return cache_data.get('transcript')
            
        except Exception as e:
            self.logger.error(f"Error loading transcript from cache path: {str(e)}")
            return None
    
    def delete_transcript(self, channel_cache_folder: str, video_id: str, title: str) -> bool:
        """
        Delete a transcript from cache.
        
        Args:
            channel_cache_folder: Channel-specific cache folder
            video_id: YouTube video ID
            title: Video title
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            cache_path = self._get_cache_path(channel_cache_folder, video_id, title)
            
            if cache_path.exists():
                cache_path.unlink()
                self.logger.info(f"Transcript deleted from cache: {cache_path}")
                return True
            else:
                self.logger.warning(f"Cache file not found for deletion: {cache_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error deleting transcript from cache: {str(e)}")
            return False
    
    def get_cache_stats(self, channel_cache_folder: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about the cache.
        
        Args:
            channel_cache_folder: Specific channel folder to analyze (optional)
            
        Returns:
            Dictionary containing cache statistics
        """
        try:
            if channel_cache_folder:
                cache_dir = Path(channel_cache_folder)
            else:
                cache_dir = self.base_cache_dir
            
            if not cache_dir.exists():
                return {
                    'total_files': 0,
                    'total_size_mb': 0.0,
                    'cache_dir': str(cache_dir),
                    'exists': False
                }
            
            # Count files and calculate total size
            total_files = 0
            total_size = 0
            
            for file_path in cache_dir.rglob('*.json'):
                if file_path.is_file():
                    total_files += 1
                    total_size += file_path.stat().st_size
            
            total_size_mb = total_size / (1024 * 1024)  # Convert to MB
            
            return {
                'total_files': total_files,
                'total_size_mb': round(total_size_mb, 2),
                'cache_dir': str(cache_dir),
                'exists': True
            }
            
        except Exception as e:
            self.logger.error(f"Error getting cache stats: {str(e)}")
            return {
                'total_files': 0,
                'total_size_mb': 0.0,
                'cache_dir': str(cache_dir) if 'cache_dir' in locals() else 'unknown',
                'exists': False,
                'error': str(e)
            }
    
    def cleanup_empty_directories(self) -> int:
        """
        Clean up empty directories in the cache.
        
        Returns:
            Number of directories removed
        """
        removed_count = 0
        
        try:
            # Walk through all directories in reverse order (deepest first)
            for dir_path in sorted(self.base_cache_dir.rglob('*'), key=lambda p: len(p.parts), reverse=True):
                if dir_path.is_dir() and not any(dir_path.iterdir()):
                    dir_path.rmdir()
                    removed_count += 1
                    self.logger.debug(f"Removed empty directory: {dir_path}")
            
            if removed_count > 0:
                self.logger.info(f"Cleaned up {removed_count} empty directories")
            
        except Exception as e:
            self.logger.error(f"Error during cache cleanup: {str(e)}")
        
        return removed_count