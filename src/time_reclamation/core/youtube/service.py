"""Main YouTube service orchestrating all YouTube functionality."""

from typing import Dict, List, Any, Optional

from src.time_reclamation.infrastructure import get_logger
from .channel_manager import YouTubeChannelManager, ChannelConfig
from .database import YouTubeDatabase
from .cache_manager import YouTubeCacheManager
from .transcript_fetcher import YouTubeTranscriptFetcher


class YouTubeService:
    """Main service for YouTube transcript scraping and management."""
    
    def __init__(self):
        """Initialize the YouTube service."""
        self.logger = get_logger()
        self.channel_manager = YouTubeChannelManager()
        self.database = YouTubeDatabase()
        self.cache_manager = YouTubeCacheManager()
        self.transcript_fetcher = YouTubeTranscriptFetcher()
        
        self.logger.info("YouTube service initialized")
    
    def scrape_all_channels(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Scrape all configured YouTube channels for new videos and transcripts.
        
        Args:
            force_refresh: Whether to force refresh even if already cached
            
        Returns:
            Dictionary with scraping results
        """
        self.logger.info("Starting YouTube channel scraping")
        
        try:
            results = self.channel_manager.process_all_channels(force_refresh)
            
            self.logger.info(f"YouTube scraping completed - "
                           f"Channels: {results['processed_channels']}/{results['total_channels']}, "
                           f"New transcripts: {results['total_new_transcripts']}, "
                           f"Cached: {results['total_cached_transcripts']}, "
                           f"Errors: {results['total_errors']}")
            
            return results
            
        except Exception as e:
            error_msg = f"Error during YouTube scraping: {str(e)}"
            self.logger.error(error_msg)
            return {
                'error': error_msg,
                'total_channels': 0,
                'processed_channels': 0,
                'total_videos_found': 0,
                'total_new_transcripts': 0,
                'total_cached_transcripts': 0,
                'total_errors': 1,
                'channel_results': []
            }
    
    def scrape_channel(self, channel_name: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Scrape a specific YouTube channel.
        
        Args:
            channel_name: Name of the channel to scrape
            force_refresh: Whether to force refresh even if already cached
            
        Returns:
            Dictionary with scraping results
        """
        self.logger.info(f"Starting scraping for channel: {channel_name}")
        
        try:
            channel = self.channel_manager.get_channel_by_name(channel_name)
            if not channel:
                error_msg = f"Channel not found: {channel_name}"
                self.logger.error(error_msg)
                return {'error': error_msg}
            
            results = self.channel_manager.process_channel(channel, force_refresh)
            
            self.logger.info(f"Channel scraping completed: {channel_name} - "
                           f"New: {results['new_transcripts']}, "
                           f"Cached: {results['cached_transcripts']}")
            
            return results
            
        except Exception as e:
            error_msg = f"Error scraping channel {channel_name}: {str(e)}"
            self.logger.error(error_msg)
            return {'error': error_msg}
    
    def get_video_transcript(self, video_url: str, language: str = 'en') -> Optional[Dict[str, Any]]:
        """
        Get transcript for a specific video URL.
        
        Args:
            video_url: YouTube video URL
            language: Language code for transcript
            
        Returns:
            Transcript data dictionary or None if not available
        """
        try:
            # Check if already in database/cache first
            existing_video = self.database.get_video_by_url(video_url)
            if existing_video and existing_video.get('transcript_path'):
                cached_transcript = self.cache_manager.load_transcript_by_path(
                    existing_video['transcript_path']
                )
                if cached_transcript:
                    self.logger.info(f"Retrieved cached transcript for: {video_url}")
                    return cached_transcript
            
            # Fetch new transcript
            self.logger.info(f"Fetching new transcript for: {video_url}")
            transcript_data = self.transcript_fetcher.get_video_transcript(video_url, language)
            
            if transcript_data and transcript_data.get('text'):
                # Extract video ID from URL for caching
                video_id = video_url.split('v=')[-1].split('&')[0] if 'v=' in video_url else 'unknown'
                title = transcript_data['metadata'].get('title', 'Untitled')
                
                # Save to cache (using default cache folder)
                cache_folder = "cache_data/youtube_transcripts/manual"
                transcript_path = self.cache_manager.save_transcript(
                    transcript_data, cache_folder, video_id, title
                )
                
                # Save to database
                if transcript_path:
                    video_data = {
                        'url': video_url,
                        'video_id': video_id,
                        'title': title,
                        'channel_name': 'Manual',
                        'channel_url': '',
                        'language': transcript_data['metadata'].get('language', language),
                        'source_type': transcript_data['metadata'].get('source_type'),
                        'total_entries': transcript_data['metadata'].get('total_entries', 0),
                        'fetched_at': transcript_data['metadata'].get('fetched_at')
                    }
                    self.database.save_video(video_data, transcript_path)
            
            return transcript_data
            
        except Exception as e:
            self.logger.error(f"Error getting video transcript: {str(e)}")
            return None
    
    def get_channels(self) -> List[ChannelConfig]:
        """
        Get all configured YouTube channels.
        
        Returns:
            List of ChannelConfig objects
        """
        return self.channel_manager.get_channels()
    
    def get_channel_stats(self) -> List[Dict[str, Any]]:
        """
        Get statistics for all configured channels.
        
        Returns:
            List of channel statistics dictionaries
        """
        return self.channel_manager.get_channel_stats()
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get overall database statistics.
        
        Returns:
            Dictionary containing database statistics
        """
        return self.database.get_database_stats()
    
    def get_unprocessed_videos(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get videos that haven't been processed by LLM yet.
        
        Args:
            limit: Maximum number of videos to return
            
        Returns:
            List of unprocessed video dictionaries
        """
        return self.database.get_unprocessed_videos(limit)
    
    def mark_video_processed(self, video_url: str, processed: bool = True) -> bool:
        """
        Mark a video as processed by LLM.
        
        Args:
            video_url: YouTube video URL
            processed: Whether the video has been processed
            
        Returns:
            True if successful, False otherwise
        """
        return self.database.mark_llm_processed(video_url, processed)
    
    def get_video_by_url(self, video_url: str) -> Optional[Dict[str, Any]]:
        """
        Get video information by URL.
        
        Args:
            video_url: YouTube video URL
            
        Returns:
            Video information dictionary or None if not found
        """
        return self.database.get_video_by_url(video_url)
    
    def get_videos_by_channel(self, channel_name: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all videos for a specific channel.
        
        Args:
            channel_name: Channel name
            limit: Maximum number of videos to return
            
        Returns:
            List of video dictionaries
        """
        channel = self.channel_manager.get_channel_by_name(channel_name)
        if not channel:
            self.logger.error(f"Channel not found: {channel_name}")
            return []
        
        return self.database.get_videos_by_channel(channel.url, limit)
    
    def cleanup_cache(self) -> Dict[str, Any]:
        """
        Clean up the cache by removing empty directories.
        
        Returns:
            Dictionary with cleanup results
        """
        try:
            removed_dirs = self.cache_manager.cleanup_empty_directories()
            
            result = {
                'success': True,
                'removed_directories': removed_dirs,
                'message': f"Cleaned up {removed_dirs} empty directories"
            }
            
            self.logger.info(result['message'])
            return result
            
        except Exception as e:
            error_msg = f"Error during cache cleanup: {str(e)}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'removed_directories': 0
            }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get overall cache statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        return self.cache_manager.get_cache_stats()


# Global YouTube service instance
_youtube_service: Optional[YouTubeService] = None


def get_youtube_service() -> YouTubeService:
    """
    Get the global YouTube service instance.
    
    Returns:
        YouTubeService instance
    """
    global _youtube_service
    if _youtube_service is None:
        _youtube_service = YouTubeService()
    return _youtube_service