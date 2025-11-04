"""YouTube channel management for handling multiple channels."""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from src.time_reclamation.config import get_app_config
from src.time_reclamation.infrastructure import get_logger
from .transcript_fetcher import YouTubeTranscriptFetcher
from .database import YouTubeDatabase
from .cache_manager import YouTubeCacheManager


@dataclass
class ChannelConfig:
    """Configuration for a YouTube channel."""
    name: str
    scrap: bool
    url: str
    max_videos: int
    language: str
    cache_folder: str


class YouTubeChannelManager:
    """Manages multiple YouTube channels and their configurations."""
    
    def __init__(self):
        """Initialize the channel manager."""
        self.config = get_app_config()
        self.logger = get_logger()
        self.transcript_fetcher = YouTubeTranscriptFetcher()
        self.database = YouTubeDatabase()
        self.cache_manager = YouTubeCacheManager()
        self._channels = self._load_channels()
    
    def _load_channels(self) -> List[ChannelConfig]:
        """
        Load channel configurations from app config.
        
        Returns:
            List of ChannelConfig objects
        """
        channels = []
        
        try:
            youtube_config = self.config.platforms.youtube
            if not youtube_config.enabled:
                self.logger.info("YouTube platform is disabled")
                return channels
            
            channel_configs = youtube_config.channels or []
            
            for channel_data in channel_configs:
                if isinstance(channel_data, dict):
                    channel = ChannelConfig(
                        name=channel_data.get('name', 'Unknown'),
                        scrap=channel_data.get('scrap', False),
                        url=channel_data.get('url', ''),
                        max_videos=channel_data.get('max_videos', 10),
                        language=channel_data.get('language', 'en'),
                        cache_folder=channel_data.get('cache_folder', 'cache_data/youtube_transcripts/default')
                    )
                    
                    if channel.url and channel.scrap:
                        channels.append(channel)
                        self.logger.debug(f"Loaded channel config: {channel.name}")
                    else:
                        self.logger.warning(f"Skipping invalid or disabled channel: {channel.name}")
            
            self.logger.info(f"Loaded {len(channels)} active YouTube channels")
            
        except Exception as e:
            self.logger.error(f"Error loading channel configurations: {str(e)}")
        
        return channels
    
    def get_channels(self) -> List[ChannelConfig]:
        """
        Get all configured channels.
        
        Returns:
            List of ChannelConfig objects
        """
        return self._channels.copy()
    
    def get_channel_by_name(self, name: str) -> Optional[ChannelConfig]:
        """
        Get a channel configuration by name.
        
        Args:
            name: Channel name
            
        Returns:
            ChannelConfig object or None if not found
        """
        for channel in self._channels:
            if channel.name == name:
                return channel
        return None
    
    def get_channel_by_url(self, url: str) -> Optional[ChannelConfig]:
        """
        Get a channel configuration by URL.
        
        Args:
            url: Channel URL
            
        Returns:
            ChannelConfig object or None if not found
        """
        for channel in self._channels:
            if channel.url == url:
                return channel
        return None
    
    def process_channel(self, channel: ChannelConfig, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Process a single channel - fetch latest videos and transcripts.
        
        Args:
            channel: Channel configuration
            force_refresh: Whether to force refresh even if already cached
            
        Returns:
            Dictionary with processing results
        """
        results = {
            'channel_name': channel.name,
            'channel_url': channel.url,
            'videos_found': 0,
            'new_transcripts': 0,
            'cached_transcripts': 0,
            'errors': [],
            'processed_videos': []
        }
        
        try:
            self.logger.info(f"Processing channel: {channel.name}")
            
            # Get latest videos from channel
            videos = self.transcript_fetcher.get_latest_videos(channel.url, channel.max_videos)
            results['videos_found'] = len(videos)
            
            if not videos:
                self.logger.warning(f"No videos found for channel: {channel.name}")
                return results
            
            for video in videos:
                video_result = self._process_video(video, channel, force_refresh)
                results['processed_videos'].append(video_result)
                
                if video_result['status'] == 'new_transcript':
                    results['new_transcripts'] += 1
                elif video_result['status'] == 'cached':
                    results['cached_transcripts'] += 1
                elif video_result['status'] == 'error':
                    results['errors'].append(video_result['error'])
            
            self.logger.info(f"Channel processing complete: {channel.name} - "
                           f"{results['new_transcripts']} new, {results['cached_transcripts']} cached")
            
        except Exception as e:
            error_msg = f"Error processing channel {channel.name}: {str(e)}"
            self.logger.error(error_msg)
            results['errors'].append(error_msg)
        
        return results
    
    def _process_video(self, video: Dict[str, Any], channel: ChannelConfig, 
                      force_refresh: bool = False) -> Dict[str, Any]:
        """
        Process a single video - check cache and fetch transcript if needed.
        
        Args:
            video: Video metadata dictionary
            channel: Channel configuration
            force_refresh: Whether to force refresh even if already cached
            
        Returns:
            Dictionary with video processing results
        """
        video_result = {
            'video_id': video.get('id'),
            'title': video.get('title'),
            'url': video.get('url'),
            'status': 'unknown',
            'transcript_path': None,
            'error': None
        }
        
        try:
            video_url = video['url']
            video_id = video.get('id')
            title = video.get('title', 'Untitled')
            
            # Check if already in database and cache (unless force refresh)
            if not force_refresh:
                # Check database first
                existing_video = self.database.get_video_by_url(video_url)
                if existing_video and existing_video.get('transcript_path'):
                    # Check if cache file still exists
                    if self.cache_manager.transcript_exists(channel.cache_folder, video_id, title):
                        video_result['status'] = 'cached'
                        video_result['transcript_path'] = existing_video['transcript_path']
                        self.logger.debug(f"Video already cached: {title}")
                        return video_result
            
            # Fetch transcript
            self.logger.info(f"Fetching transcript for: {title}")
            transcript_data = self.transcript_fetcher.get_video_transcript(video_url, channel.language)
            
            if not transcript_data or not transcript_data.get('text'):
                video_result['status'] = 'no_transcript'
                video_result['error'] = transcript_data.get('metadata', {}).get('error', 'No transcript available')
                self.logger.warning(f"No transcript available for: {title}")
                
                # Still save to database to avoid re-checking
                video_data = {
                    'url': video_url,
                    'video_id': video_id,
                    'title': title,
                    'channel_name': channel.name,
                    'channel_url': channel.url,
                    'language': channel.language,
                    'fetched_at': video.get('fetched_at')
                }
                self.database.save_video(video_data)
                
                return video_result
            
            # Save transcript to cache
            transcript_path = self.cache_manager.save_transcript(
                transcript_data, channel.cache_folder, video_id, title
            )
            
            if transcript_path:
                # Save to database
                video_data = {
                    'url': video_url,
                    'video_id': video_id,
                    'title': title,
                    'channel_name': channel.name,
                    'channel_url': channel.url,
                    'language': transcript_data['metadata'].get('language', channel.language),
                    'source_type': transcript_data['metadata'].get('source_type'),
                    'total_entries': transcript_data['metadata'].get('total_entries', 0),
                    'fetched_at': transcript_data['metadata'].get('fetched_at')
                }
                
                if self.database.save_video(video_data, transcript_path):
                    video_result['status'] = 'new_transcript'
                    video_result['transcript_path'] = transcript_path
                    self.logger.info(f"Successfully processed video: {title}")
                else:
                    video_result['status'] = 'error'
                    video_result['error'] = 'Failed to save to database'
            else:
                video_result['status'] = 'error'
                video_result['error'] = 'Failed to save transcript to cache'
                
        except Exception as e:
            error_msg = f"Error processing video {video_result['title']}: {str(e)}"
            self.logger.error(error_msg)
            video_result['status'] = 'error'
            video_result['error'] = error_msg
        
        return video_result
    
    def process_all_channels(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Process all configured channels.
        
        Args:
            force_refresh: Whether to force refresh even if already cached
            
        Returns:
            Dictionary with overall processing results
        """
        overall_results = {
            'total_channels': len(self._channels),
            'processed_channels': 0,
            'total_videos_found': 0,
            'total_new_transcripts': 0,
            'total_cached_transcripts': 0,
            'total_errors': 0,
            'channel_results': []
        }
        
        self.logger.info(f"Starting to process {len(self._channels)} channels")
        
        for channel in self._channels:
            try:
                channel_result = self.process_channel(channel, force_refresh)
                overall_results['channel_results'].append(channel_result)
                overall_results['processed_channels'] += 1
                overall_results['total_videos_found'] += channel_result['videos_found']
                overall_results['total_new_transcripts'] += channel_result['new_transcripts']
                overall_results['total_cached_transcripts'] += channel_result['cached_transcripts']
                overall_results['total_errors'] += len(channel_result['errors'])
                
            except Exception as e:
                error_msg = f"Failed to process channel {channel.name}: {str(e)}"
                self.logger.error(error_msg)
                overall_results['total_errors'] += 1
        
        self.logger.info(f"Finished processing all channels - "
                        f"{overall_results['total_new_transcripts']} new transcripts, "
                        f"{overall_results['total_cached_transcripts']} cached, "
                        f"{overall_results['total_errors']} errors")
        
        return overall_results
    
    def get_channel_stats(self) -> List[Dict[str, Any]]:
        """
        Get statistics for all channels.
        
        Returns:
            List of channel statistics dictionaries
        """
        stats = []
        
        for channel in self._channels:
            try:
                # Get database stats for this channel
                videos = self.database.get_videos_by_channel(channel.url)
                videos_with_transcripts = [v for v in videos if v.get('transcript_path')]
                processed_videos = [v for v in videos if v.get('llm_processed')]
                
                # Get cache stats
                cache_stats = self.cache_manager.get_cache_stats(channel.cache_folder)
                
                channel_stats = {
                    'name': channel.name,
                    'url': channel.url,
                    'enabled': channel.scrap,
                    'max_videos': channel.max_videos,
                    'language': channel.language,
                    'total_videos': len(videos),
                    'videos_with_transcripts': len(videos_with_transcripts),
                    'llm_processed': len(processed_videos),
                    'cache_files': cache_stats.get('total_files', 0),
                    'cache_size_mb': cache_stats.get('total_size_mb', 0.0)
                }
                
                stats.append(channel_stats)
                
            except Exception as e:
                self.logger.error(f"Error getting stats for channel {channel.name}: {str(e)}")
                stats.append({
                    'name': channel.name,
                    'url': channel.url,
                    'error': str(e)
                })
        
        return stats