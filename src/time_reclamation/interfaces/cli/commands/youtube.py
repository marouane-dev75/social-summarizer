"""YouTube command for managing YouTube transcript scraping."""

import json
from typing import List
from .base import BaseCommand
from src.time_reclamation.core.youtube import get_youtube_service


class YouTubeCommand(BaseCommand):
    """Command for YouTube transcript scraping and management."""
    
    @property
    def name(self) -> str:
        """Return the command name."""
        return "youtube"
    
    @property
    def description(self) -> str:
        """Return the command description."""
        return "Manage YouTube transcript scraping and channel monitoring"
    
    @property
    def aliases(self) -> List[str]:
        """Return command aliases."""
        return ["yt"]
    
    @property
    def usage(self) -> str:
        """Return command usage string."""
        return """python -m time_reclamation youtube <subcommand> [options]

SUBCOMMANDS:
  scrape [channel_name]     - Scrape all channels or specific channel
  stats                     - Show YouTube statistics
  channels                  - List configured channels
  video <url> [language]    - Get transcript for specific video
  unprocessed [limit]       - Show unprocessed videos
  mark-processed <url>      - Mark video as LLM processed
  cache-stats               - Show cache statistics
  cleanup                   - Clean up empty cache directories
  help                      - Show this help message

EXAMPLES:
  python -m time_reclamation youtube scrape
  python -m time_reclamation youtube scrape "TechWizard9000"
  python -m time_reclamation youtube stats
  python -m time_reclamation youtube video "https://www.youtube.com/watch?v=VIDEO_ID"
  python -m time_reclamation youtube unprocessed 10"""
    
    def execute(self, args: List[str]) -> int:
        """
        Execute the YouTube command.
        
        Args:
            args: Command line arguments
            
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        try:
            if not args or args[0] in ["--help", "-h", "help"]:
                self.show_help()
                return 0
            
            subcommand = args[0].lower()
            subcommand_args = args[1:] if len(args) > 1 else []
            
            # Route to appropriate subcommand
            if subcommand == "scrape":
                return self._handle_scrape(subcommand_args)
            elif subcommand == "stats":
                return self._handle_stats(subcommand_args)
            elif subcommand == "channels":
                return self._handle_channels(subcommand_args)
            elif subcommand == "video":
                return self._handle_video(subcommand_args)
            elif subcommand == "unprocessed":
                return self._handle_unprocessed(subcommand_args)
            elif subcommand == "mark-processed":
                return self._handle_mark_processed(subcommand_args)
            elif subcommand == "cache-stats":
                return self._handle_cache_stats(subcommand_args)
            elif subcommand == "cleanup":
                return self._handle_cleanup(subcommand_args)
            else:
                return self.handle_error(f"Unknown subcommand: {subcommand}")
                
        except Exception as e:
            return self.handle_error(f"YouTube command failed: {str(e)}")
    
    def _handle_scrape(self, args: List[str]) -> int:
        """Handle the scrape subcommand."""
        try:
            youtube_service = get_youtube_service()
            force_refresh = "--force" in args
            
            if force_refresh:
                args.remove("--force")
            
            if args:
                # Scrape specific channel
                channel_name = args[0]
                self.logger.info(f"Scraping channel: {channel_name}")
                
                results = youtube_service.scrape_channel(channel_name, force_refresh)
                
                if 'error' in results:
                    return self.handle_error(results['error'])
                
                self.logger.print_header(f"Channel Scraping Results: {channel_name}")
                self.logger.print_bullet(f"Videos found: {results['videos_found']}")
                self.logger.print_bullet(f"New transcripts: {results['new_transcripts']}")
                self.logger.print_bullet(f"Cached transcripts: {results['cached_transcripts']}")
                
                if results['errors']:
                    self.logger.print_section("ERRORS")
                    for error in results['errors']:
                        self.logger.error(f"  {error}")
                
            else:
                # Scrape all channels
                self.logger.info("Scraping all configured channels")
                
                results = youtube_service.scrape_all_channels(force_refresh)
                
                if 'error' in results:
                    return self.handle_error(results['error'])
                
                self.logger.print_header("All Channels Scraping Results")
                self.logger.print_bullet(f"Channels processed: {results['processed_channels']}/{results['total_channels']}")
                self.logger.print_bullet(f"Total videos found: {results['total_videos_found']}")
                self.logger.print_bullet(f"New transcripts: {results['total_new_transcripts']}")
                self.logger.print_bullet(f"Cached transcripts: {results['total_cached_transcripts']}")
                self.logger.print_bullet(f"Total errors: {results['total_errors']}")
                
                # Show per-channel results
                if results['channel_results']:
                    self.logger.print_section("PER-CHANNEL RESULTS")
                    for channel_result in results['channel_results']:
                        self.logger.print_bullet(
                            f"{channel_result['channel_name']}: "
                            f"{channel_result['new_transcripts']} new, "
                            f"{channel_result['cached_transcripts']} cached, "
                            f"{len(channel_result['errors'])} errors"
                        )
            
            return self.handle_success("Scraping completed successfully")
            
        except Exception as e:
            return self.handle_error(f"Scraping failed: {str(e)}")
    
    def _handle_stats(self, args: List[str]) -> int:
        """Handle the stats subcommand."""
        try:
            youtube_service = get_youtube_service()
            
            # Get database stats
            db_stats = youtube_service.get_database_stats()
            
            # Get channel stats
            channel_stats = youtube_service.get_channel_stats()
            
            # Get cache stats
            cache_stats = youtube_service.get_cache_stats()
            
            self.logger.print_header("YouTube Statistics")
            
            # Database statistics
            self.logger.print_section("DATABASE STATISTICS")
            self.logger.print_bullet(f"Total videos: {db_stats.get('total_videos', 0)}")
            self.logger.print_bullet(f"Videos with transcripts: {db_stats.get('videos_with_transcripts', 0)}")
            self.logger.print_bullet(f"LLM processed: {db_stats.get('llm_processed', 0)}")
            self.logger.print_bullet(f"Unprocessed: {db_stats.get('unprocessed', 0)}")
            self.logger.print_bullet(f"Unique channels: {db_stats.get('unique_channels', 0)}")
            
            # Cache statistics
            self.logger.print_section("CACHE STATISTICS")
            self.logger.print_bullet(f"Total cache files: {cache_stats.get('total_files', 0)}")
            self.logger.print_bullet(f"Cache size: {cache_stats.get('total_size_mb', 0.0):.2f} MB")
            self.logger.print_bullet(f"Cache directory: {cache_stats.get('cache_dir', 'N/A')}")
            
            # Channel statistics
            if channel_stats:
                self.logger.print_section("CHANNEL STATISTICS")
                for channel in channel_stats:
                    if 'error' not in channel:
                        self.logger.print_bullet(
                            f"{channel['name']}: {channel['total_videos']} videos, "
                            f"{channel['videos_with_transcripts']} with transcripts, "
                            f"{channel['cache_files']} cache files ({channel['cache_size_mb']:.2f} MB)"
                        )
                    else:
                        self.logger.print_bullet(f"{channel['name']}: Error - {channel['error']}")
            
            return self.handle_success()
            
        except Exception as e:
            return self.handle_error(f"Failed to get statistics: {str(e)}")
    
    def _handle_channels(self, args: List[str]) -> int:
        """Handle the channels subcommand."""
        try:
            youtube_service = get_youtube_service()
            channels = youtube_service.get_channels()
            
            if not channels:
                self.logger.warning("No YouTube channels configured")
                return 0
            
            self.logger.print_header("Configured YouTube Channels")
            
            for channel in channels:
                self.logger.print_section(channel.name)
                self.logger.print_bullet(f"URL: {channel.url}")
                self.logger.print_bullet(f"Scraping enabled: {'Yes' if channel.scrap else 'No'}")
                self.logger.print_bullet(f"Max videos: {channel.max_videos}")
                self.logger.print_bullet(f"Language: {channel.language}")
                self.logger.print_bullet(f"Cache folder: {channel.cache_folder}")
            
            return self.handle_success()
            
        except Exception as e:
            return self.handle_error(f"Failed to list channels: {str(e)}")
    
    def _handle_video(self, args: List[str]) -> int:
        """Handle the video subcommand."""
        try:
            if not args:
                return self.handle_error("Video URL is required")
            
            video_url = args[0]
            language = args[1] if len(args) > 1 else 'en'
            
            youtube_service = get_youtube_service()
            
            self.logger.info(f"Fetching transcript for: {video_url}")
            transcript_data = youtube_service.get_video_transcript(video_url, language)
            
            if not transcript_data:
                return self.handle_error("Failed to fetch transcript")
            
            if not transcript_data.get('text'):
                error_msg = transcript_data.get('metadata', {}).get('error', 'No transcript available')
                return self.handle_error(f"No transcript available: {error_msg}")
            
            metadata = transcript_data.get('metadata', {})
            
            self.logger.print_header("Video Transcript")
            self.logger.print_section("METADATA")
            self.logger.print_bullet(f"Title: {metadata.get('title', 'N/A')}")
            self.logger.print_bullet(f"Video ID: {metadata.get('video_id', 'N/A')}")
            self.logger.print_bullet(f"Language: {metadata.get('language', 'N/A')}")
            self.logger.print_bullet(f"Source: {metadata.get('source_type', 'N/A')}")
            self.logger.print_bullet(f"Total entries: {metadata.get('total_entries', 0)}")
            
            # Show first few entries as preview
            entries = transcript_data.get('entries', [])
            if entries:
                self.logger.print_section("TRANSCRIPT PREVIEW (First 3 entries)")
                for i, entry in enumerate(entries[:3]):
                    start_min = int(entry['start'] // 60)
                    start_sec = int(entry['start'] % 60)
                    self.logger.print_bullet(f"[{start_min:02d}:{start_sec:02d}] {entry['text']}")
            
            # Option to show full transcript
            if "--full" in args:
                self.logger.print_section("FULL TRANSCRIPT")
                self.logger.info(transcript_data['text'])
            else:
                self.logger.print_section("FULL TRANSCRIPT (First 500 characters)")
                text = transcript_data['text']
                preview = text[:500] + "..." if len(text) > 500 else text
                self.logger.info(preview)
                self.logger.info("Use --full flag to see complete transcript")
            
            return self.handle_success()
            
        except Exception as e:
            return self.handle_error(f"Failed to get video transcript: {str(e)}")
    
    def _handle_unprocessed(self, args: List[str]) -> int:
        """Handle the unprocessed subcommand."""
        try:
            limit = None
            if args:
                try:
                    limit = int(args[0])
                except ValueError:
                    return self.handle_error("Limit must be a number")
            
            youtube_service = get_youtube_service()
            videos = youtube_service.get_unprocessed_videos(limit)
            
            if not videos:
                self.logger.info("No unprocessed videos found")
                return 0
            
            self.logger.print_header(f"Unprocessed Videos ({len(videos)})")
            
            for i, video in enumerate(videos, 1):
                self.logger.print_section(f"{i}. {video.get('title', 'Untitled')}")
                self.logger.print_bullet(f"URL: {video.get('url', 'N/A')}")
                self.logger.print_bullet(f"Channel: {video.get('channel_name', 'N/A')}")
                self.logger.print_bullet(f"Language: {video.get('language', 'N/A')}")
                self.logger.print_bullet(f"Entries: {video.get('total_entries', 0)}")
                self.logger.print_bullet(f"Created: {video.get('created_at', 'N/A')}")
            
            return self.handle_success()
            
        except Exception as e:
            return self.handle_error(f"Failed to get unprocessed videos: {str(e)}")
    
    def _handle_mark_processed(self, args: List[str]) -> int:
        """Handle the mark-processed subcommand."""
        try:
            if not args:
                return self.handle_error("Video URL is required")
            
            video_url = args[0]
            youtube_service = get_youtube_service()
            
            success = youtube_service.mark_video_processed(video_url, True)
            
            if success:
                return self.handle_success(f"Video marked as processed: {video_url}")
            else:
                return self.handle_error("Failed to mark video as processed")
                
        except Exception as e:
            return self.handle_error(f"Failed to mark video as processed: {str(e)}")
    
    def _handle_cache_stats(self, args: List[str]) -> int:
        """Handle the cache-stats subcommand."""
        try:
            youtube_service = get_youtube_service()
            cache_stats = youtube_service.get_cache_stats()
            
            self.logger.print_header("Cache Statistics")
            self.logger.print_bullet(f"Total files: {cache_stats.get('total_files', 0)}")
            self.logger.print_bullet(f"Total size: {cache_stats.get('total_size_mb', 0.0):.2f} MB")
            self.logger.print_bullet(f"Cache directory: {cache_stats.get('cache_dir', 'N/A')}")
            self.logger.print_bullet(f"Directory exists: {'Yes' if cache_stats.get('exists', False) else 'No'}")
            
            if 'error' in cache_stats:
                self.logger.error(f"Cache error: {cache_stats['error']}")
            
            return self.handle_success()
            
        except Exception as e:
            return self.handle_error(f"Failed to get cache statistics: {str(e)}")
    
    def _handle_cleanup(self, args: List[str]) -> int:
        """Handle the cleanup subcommand."""
        try:
            youtube_service = get_youtube_service()
            result = youtube_service.cleanup_cache()
            
            if result.get('success', False):
                return self.handle_success(result.get('message', 'Cache cleanup completed'))
            else:
                return self.handle_error(result.get('error', 'Cache cleanup failed'))
                
        except Exception as e:
            return self.handle_error(f"Cache cleanup failed: {str(e)}")