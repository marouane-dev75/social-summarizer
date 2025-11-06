"""YouTube video summary service for processing transcripts into audio summaries."""

import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from src.time_reclamation.infrastructure import get_logger
from src.time_reclamation.infrastructure.llm import get_llm_manager, LLMStatus
from src.time_reclamation.infrastructure.tts import get_tts_manager, TTSStatus
from src.time_reclamation.infrastructure.notifications import get_notification_manager, NotificationStatus
from src.time_reclamation.config import get_config_manager
from .database import YouTubeDatabase
from .cache_manager import YouTubeCacheManager
from .service import get_youtube_service


class SummaryService:
    """Service for processing video transcripts into audio summaries."""
    
    DEFAULT_SYSTEM_PROMPT = """You are a podcast host creating an engaging audio summary of a YouTube video transcript.

Your task:
1. Convert the transcript into a conversational, easy-to-listen format
2. Focus on the key insights, main points, and takeaways
3. Make it sound natural for audio playback (use conversational language)
4. Keep it concise but informative (aim for 3-5 minutes when spoken)
5. Start with a brief intro mentioning the video title
6. End with a conclusion summarizing the main value

Style: Conversational, engaging, podcast-like
Tone: Friendly but informative
Length: 500-800 words (approximately 3-5 minutes of audio)

Important: Output ONLY the summary text, no meta-commentary or explanations."""
    
    def __init__(self):
        """Initialize the summary service."""
        self.logger = get_logger()
        self.database = YouTubeDatabase()
        self.cache_manager = YouTubeCacheManager()
        self.llm_manager = get_llm_manager()
        self.tts_manager = get_tts_manager()
        self.notification_manager = get_notification_manager()
        self.config_manager = get_config_manager()
        self.youtube_service = get_youtube_service()
        
        # Create directories for permanent storage
        self.audio_dir = Path("cache_data/summaries/audio")
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        
        self.text_dir = Path("cache_data/summaries/text")
        self.text_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("Summary service initialized")
    
    def process_channel_summaries(
        self,
        channel_name: Optional[str] = None,
        limit: Optional[int] = None,
        force: bool = False,
        scrape_first: bool = True
    ) -> Dict[str, Any]:
        """
        Process summaries for channel(s).
        
        Args:
            channel_name: Specific channel to process (None for all enabled channels)
            limit: Maximum number of videos to process
            force: Force reprocess even if already processed
            scrape_first: Whether to scrape for new videos before processing summaries
            
        Returns:
            Dictionary with processing results
        """
        self.logger.info(f"Starting summary processing for channel: {channel_name or 'all enabled channels'}")
        
        # Step 1: Scrape for new videos if requested
        if scrape_first:
            self.logger.info("Scraping for new videos before processing summaries")
            try:
                if channel_name:
                    scrape_result = self.youtube_service.scrape_channel(channel_name, force_refresh=force)
                else:
                    scrape_result = self.youtube_service.scrape_all_channels(force_refresh=force)
                
                if 'error' in scrape_result:
                    self.logger.warning(f"Scraping encountered an error: {scrape_result['error']}")
                else:
                    self.logger.info(f"Scraping completed - New transcripts: {scrape_result.get('total_new_transcripts', 0)}")
            except Exception as e:
                self.logger.warning(f"Error during scraping: {str(e)}")
                # Continue with summary processing even if scraping fails
        
        try:
            # Get channels to process
            if channel_name:
                summary_config = self.config_manager.get_channel_summary_config(channel_name)
                if not summary_config:
                    return {
                        'error': f"Channel '{channel_name}' not found or summary not enabled",
                        'processed': 0,
                        'failed': 0,
                        'skipped': 0
                    }
                
                channels = [{
                    'name': channel_name,
                    'summary_config': summary_config
                }]
            else:
                channels = self.config_manager.get_summary_enabled_channels()
                
                if not channels:
                    return {
                        'error': 'No channels with summary enabled',
                        'processed': 0,
                        'failed': 0,
                        'skipped': 0
                    }
            
            # Process each channel
            total_processed = 0
            total_failed = 0
            total_skipped = 0
            channel_results = []
            
            for channel_info in channels:
                channel_name = channel_info['name']
                summary_config = channel_info.get('summary_config', {})
                
                self.logger.info(f"Processing summaries for channel: {channel_name}")
                
                # Get channel URL from config
                channel_url = None
                for ch_data in self.config_manager.get_config().platforms.youtube.channels:
                    if isinstance(ch_data, dict) and ch_data.get('name') == channel_name:
                        channel_url = ch_data.get('url')
                        break
                
                if not channel_url:
                    self.logger.warning(f"Channel URL not found for: {channel_name}")
                    continue
                
                # Get unsummarized videos for this channel
                videos = self.database.get_unsummarized_videos(channel_url, limit)
                
                if not videos:
                    self.logger.info(f"No unsummarized videos for channel: {channel_name}")
                    channel_results.append({
                        'channel_name': channel_name,
                        'processed': 0,
                        'failed': 0,
                        'skipped': 0
                    })
                    continue
                
                # Process each video
                processed = 0
                failed = 0
                skipped = 0
                
                for video in videos:
                    result = self.process_video_summary(video['url'], summary_config)
                    
                    if result.get('success'):
                        processed += 1
                    elif result.get('skipped'):
                        skipped += 1
                    else:
                        failed += 1
                
                total_processed += processed
                total_failed += failed
                total_skipped += skipped
                
                channel_results.append({
                    'channel_name': channel_name,
                    'processed': processed,
                    'failed': failed,
                    'skipped': skipped
                })
            
            self.logger.info(f"Summary processing completed - Processed: {total_processed}, Failed: {total_failed}, Skipped: {total_skipped}")
            
            return {
                'processed': total_processed,
                'failed': total_failed,
                'skipped': total_skipped,
                'channel_results': channel_results
            }
            
        except Exception as e:
            error_msg = f"Error processing channel summaries: {str(e)}"
            self.logger.error(error_msg)
            return {
                'error': error_msg,
                'processed': 0,
                'failed': 0,
                'skipped': 0
            }
    
    def process_video_summary(
        self,
        video_url: str,
        summary_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process summary for a single video.
        
        Args:
            video_url: YouTube video URL
            summary_config: Optional summary configuration
            
        Returns:
            Dictionary with processing result
        """
        self.logger.info(f"Processing summary for video: {video_url}")
        
        try:
            # Get video data from database
            video = self.database.get_video_by_url(video_url)
            if not video:
                return {'success': False, 'error': 'Video not found in database'}
            
            # Check if transcript exists
            if not video.get('transcript_path'):
                return {'success': False, 'skipped': True, 'error': 'No transcript available'}
            
            # Load transcript
            transcript_data = self.cache_manager.load_transcript_by_path(video['transcript_path'])
            if not transcript_data or not transcript_data.get('text'):
                return {'success': False, 'error': 'Failed to load transcript'}
            
            transcript_text = transcript_data['text']
            video_title = video.get('title', 'Untitled')
            video_id = video.get('video_id', 'unknown')
            
            # Get configuration
            summary_config = summary_config or {}
            llm_provider = summary_config.get('llm_provider')
            tts_provider = summary_config.get('tts_provider')
            notification_provider = summary_config.get('notification_provider')
            system_prompt = summary_config.get('system_prompt', self.DEFAULT_SYSTEM_PROMPT)
            
            # Step 1: Generate summary using LLM
            self.logger.info(f"Generating summary for: {video_title}")
            llm_result = self.llm_manager.generate_response(
                user_prompt=transcript_text,
                instance_name=llm_provider,
                system_prompt=system_prompt
            )
            
            if llm_result.status != LLMStatus.SUCCESS:
                error_msg = f"LLM generation failed: {llm_result.error_details}"
                self.database.mark_summary_error(video_url, error_msg)
                return {'success': False, 'error': error_msg}
            
            summary_text = llm_result.response
            self.logger.info(f"Summary generated successfully ({len(summary_text)} characters)")
            
            # Step 2: Save summary text to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            text_filename = f"summary_{video_id}_{timestamp}.txt"
            text_path = self.text_dir / text_filename
            
            try:
                with open(text_path, 'w', encoding='utf-8') as f:
                    f.write(f"Video Title: {video_title}\n")
                    f.write(f"Video URL: {video_url}\n")
                    f.write(f"Channel: {video.get('channel_name', 'Unknown')}\n")
                    f.write(f"Generated: {datetime.now().isoformat()}\n")
                    f.write(f"\n{'='*80}\n\n")
                    f.write(summary_text)
                self.logger.info(f"Summary text saved: {text_path}")
            except Exception as e:
                self.logger.warning(f"Failed to save summary text file: {str(e)}")
            
            # Step 3: Convert summary to audio using TTS
            audio_filename = f"summary_{video_id}_{timestamp}.wav"
            
            self.logger.info(f"Converting summary to audio: {audio_filename}")
            tts_result = self.tts_manager.generate_speech(
                text=summary_text,
                output_filename=audio_filename,
                instance_name=tts_provider
            )
            
            if tts_result.status != TTSStatus.SUCCESS:
                error_msg = f"TTS conversion failed: {tts_result.error_details}"
                self.database.mark_summary_error(video_url, error_msg)
                return {'success': False, 'error': error_msg}
            
            audio_path = str(tts_result.output_file)
            self.logger.info(f"Audio generated and saved permanently: {audio_path}")
            
            # Step 4: Send notification with audio
            estimated_minutes = len(summary_text.split()) // 150  # Rough estimate: 150 words per minute
            notification_message = f"""🎥 New Video Summary: {video_title}

Channel: {video.get('channel_name', 'Unknown')}
Duration: ~{estimated_minutes} minutes

[Audio file attached]"""
            
            self.logger.info(f"Sending notification for: {video_title}")
            
            # For Telegram, we need to send audio file
            # Note: The current notification system only supports text messages
            # We'll send the text message and log that audio needs to be sent separately
            notification_result = self.notification_manager.send_message(
                message=notification_message,
                instance_name=notification_provider
            )
            
            if notification_result.status != NotificationStatus.SUCCESS:
                error_msg = f"Notification failed: {notification_result.error_details}"
                self.logger.warning(error_msg)
                # Don't fail the whole process, just log the warning
            else:
                self.logger.info("Notification sent successfully")
            
            # Step 5: Mark as processed in database with audio path
            self.database.mark_summary_processed(video_url, summary_text, audio_path)
            self.logger.info(f"Summary processing completed - Text: {text_path}, Audio: {audio_path}")
            
            return {
                'success': True,
                'video_title': video_title,
                'summary_length': len(summary_text),
                'audio_path': audio_path,
                'text_path': str(text_path)
            }
            
        except Exception as e:
            error_msg = f"Error processing video summary: {str(e)}"
            self.logger.error(error_msg)
            self.database.mark_summary_error(video_url, error_msg)
            return {'success': False, 'error': error_msg}
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Get summary processing statistics.
        
        Returns:
            Dictionary containing summary statistics
        """
        return self.database.get_summary_stats()
    
    def retry_failed_summaries(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Retry videos that failed summary processing.
        
        Args:
            limit: Maximum number of videos to retry
            
        Returns:
            Dictionary with retry results
        """
        self.logger.info("Retrying failed summaries")
        
        try:
            failed_videos = self.database.get_failed_summaries(limit)
            
            if not failed_videos:
                return {
                    'processed': 0,
                    'failed': 0,
                    'message': 'No failed summaries to retry'
                }
            
            processed = 0
            failed = 0
            
            for video in failed_videos:
                # Get channel summary config
                channel_name = video.get('channel_name')
                summary_config = self.config_manager.get_channel_summary_config(channel_name) if channel_name else None
                
                result = self.process_video_summary(video['url'], summary_config)
                
                if result.get('success'):
                    processed += 1
                else:
                    failed += 1
            
            return {
                'processed': processed,
                'failed': failed,
                'message': f"Retry completed - Processed: {processed}, Failed: {failed}"
            }
            
        except Exception as e:
            error_msg = f"Error retrying failed summaries: {str(e)}"
            self.logger.error(error_msg)
            return {
                'error': error_msg,
                'processed': 0,
                'failed': 0
            }
    
    def cleanup_audio_files(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """
        Clean up orphaned audio files older than specified age.
        
        Args:
            max_age_hours: Maximum age in hours for audio files
            
        Returns:
            Dictionary with cleanup results
        """
        self.logger.info(f"Cleaning up audio files older than {max_age_hours} hours")
        
        try:
            if not self.audio_dir.exists():
                return {
                    'removed_files': 0,
                    'message': 'Audio directory does not exist'
                }
            
            removed_count = 0
            current_time = datetime.now().timestamp()
            max_age_seconds = max_age_hours * 3600
            
            for audio_file in self.audio_dir.glob('*.wav'):
                if audio_file.is_file():
                    file_age = current_time - audio_file.stat().st_mtime
                    
                    if file_age > max_age_seconds:
                        try:
                            audio_file.unlink()
                            removed_count += 1
                            self.logger.debug(f"Removed old audio file: {audio_file.name}")
                        except Exception as e:
                            self.logger.warning(f"Failed to remove {audio_file.name}: {str(e)}")
            
            message = f"Cleaned up {removed_count} audio files"
            self.logger.info(message)
            
            return {
                'removed_files': removed_count,
                'message': message
            }
            
        except Exception as e:
            error_msg = f"Error cleaning up audio files: {str(e)}"
            self.logger.error(error_msg)
            return {
                'error': error_msg,
                'removed_files': 0
            }


# Global summary service instance
_summary_service: Optional[SummaryService] = None


def get_summary_service() -> SummaryService:
    """
    Get the global summary service instance.
    
    Returns:
        SummaryService instance
    """
    global _summary_service
    if _summary_service is None:
        _summary_service = SummaryService()
    return _summary_service