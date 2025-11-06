"""YouTube database operations for tracking videos and transcripts."""

import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path

from src.time_reclamation.infrastructure.database import get_database_manager
from src.time_reclamation.infrastructure import get_logger


class YouTubeDatabase:
    """Handles database operations for YouTube videos and transcripts."""
    
    def __init__(self):
        """Initialize the YouTube database manager."""
        self.db_manager = get_database_manager()
        self.logger = get_logger()
        self._initialize_tables()
    
    def _initialize_tables(self) -> None:
        """Initialize YouTube-specific database tables."""
        try:
            with self.db_manager.get_connection() as conn:
                # Create youtube_videos table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS youtube_videos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT UNIQUE NOT NULL,
                        video_id TEXT NOT NULL,
                        title TEXT,
                        channel_name TEXT,
                        channel_url TEXT,
                        transcript_path TEXT,
                        language TEXT,
                        source_type TEXT,
                        total_entries INTEGER DEFAULT 0,
                        summary_processed BOOLEAN DEFAULT FALSE,
                        summary_text TEXT,
                        summary_audio_path TEXT,
                        summary_processed_at TIMESTAMP,
                        summary_error TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        fetched_at TEXT
                    )
                """)
                
                # Create index on url for faster lookups
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_youtube_videos_url 
                    ON youtube_videos(url)
                """)
                
                # Create index on video_id for faster lookups
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_youtube_videos_video_id 
                    ON youtube_videos(video_id)
                """)
                
                # Create index on channel_url for faster channel queries
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_youtube_videos_channel_url 
                    ON youtube_videos(channel_url)
                """)
                
                conn.commit()
                self.logger.debug("YouTube database tables initialized successfully")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize YouTube database tables: {str(e)}")
            raise
    
    def video_exists(self, video_url: str) -> bool:
        """
        Check if a video URL already exists in the database.
        
        Args:
            video_url: YouTube video URL
            
        Returns:
            True if video exists, False otherwise
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT 1 FROM youtube_videos WHERE url = ? LIMIT 1",
                    (video_url,)
                )
                return cursor.fetchone() is not None
                
        except Exception as e:
            self.logger.error(f"Error checking if video exists: {str(e)}")
            return False
    
    def get_video_by_url(self, video_url: str) -> Optional[Dict[str, Any]]:
        """
        Get video information by URL.
        
        Args:
            video_url: YouTube video URL
            
        Returns:
            Video information dictionary or None if not found
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM youtube_videos WHERE url = ?",
                    (video_url,)
                )
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting video by URL: {str(e)}")
            return None
    
    def save_video(self, video_data: Dict[str, Any], transcript_path: Optional[str] = None) -> bool:
        """
        Save or update video information in the database.
        
        Args:
            video_data: Video metadata dictionary
            transcript_path: Path to saved transcript file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_manager.get_connection() as conn:
                # Check if video already exists
                existing = self.get_video_by_url(video_data['url'])
                current_time = datetime.now(timezone.utc).isoformat()
                
                if existing:
                    # Update existing record
                    conn.execute("""
                        UPDATE youtube_videos 
                        SET title = ?, channel_name = ?, channel_url = ?, 
                            transcript_path = ?, language = ?, source_type = ?,
                            total_entries = ?, updated_at = ?, fetched_at = ?
                        WHERE url = ?
                    """, (
                        video_data.get('title'),
                        video_data.get('channel_name'),
                        video_data.get('channel_url'),
                        transcript_path,
                        video_data.get('language'),
                        video_data.get('source_type'),
                        video_data.get('total_entries', 0),
                        current_time,
                        video_data.get('fetched_at'),
                        video_data['url']
                    ))
                    self.logger.debug(f"Updated existing video record: {video_data['url']}")
                else:
                    # Insert new record
                    conn.execute("""
                        INSERT INTO youtube_videos 
                        (url, video_id, title, channel_name, channel_url, 
                         transcript_path, language, source_type, total_entries, 
                         created_at, updated_at, fetched_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        video_data['url'],
                        video_data.get('video_id'),
                        video_data.get('title'),
                        video_data.get('channel_name'),
                        video_data.get('channel_url'),
                        transcript_path,
                        video_data.get('language'),
                        video_data.get('source_type'),
                        video_data.get('total_entries', 0),
                        current_time,
                        current_time,
                        video_data.get('fetched_at')
                    ))
                    self.logger.debug(f"Inserted new video record: {video_data['url']}")
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Error saving video: {str(e)}")
            return False
    
    def get_videos_by_channel(self, channel_url: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all videos for a specific channel.
        
        Args:
            channel_url: YouTube channel URL
            limit: Maximum number of videos to return
            
        Returns:
            List of video dictionaries
        """
        try:
            with self.db_manager.get_connection() as conn:
                query = "SELECT * FROM youtube_videos WHERE channel_url = ? ORDER BY created_at DESC"
                params = [channel_url]
                
                if limit:
                    query += " LIMIT ?"
                    params.append(limit)
                
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Error getting videos by channel: {str(e)}")
            return []
    
    def mark_llm_processed(self, video_url: str, processed: bool = True) -> bool:
        """
        Mark a video as processed by LLM.
        
        Args:
            video_url: YouTube video URL
            processed: Whether the video has been processed
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_manager.get_connection() as conn:
                conn.execute(
                    "UPDATE youtube_videos SET llm_processed = ?, updated_at = ? WHERE url = ?",
                    (processed, datetime.now(timezone.utc).isoformat(), video_url)
                )
                conn.commit()
                self.logger.debug(f"Marked video as LLM processed: {video_url}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error marking video as LLM processed: {str(e)}")
            return False
    
    def get_unprocessed_videos(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get videos that haven't been processed by LLM yet.
        
        Args:
            limit: Maximum number of videos to return
            
        Returns:
            List of unprocessed video dictionaries
        """
        try:
            with self.db_manager.get_connection() as conn:
                query = """
                    SELECT * FROM youtube_videos 
                    WHERE llm_processed = FALSE AND transcript_path IS NOT NULL
                    ORDER BY created_at ASC
                """
                params = []
                
                if limit:
                    query += " LIMIT ?"
                    params.append(limit)
                
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Error getting unprocessed videos: {str(e)}")
            return []
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the YouTube videos database.
        
        Returns:
            Dictionary containing database statistics
        """
        try:
            with self.db_manager.get_connection() as conn:
                # Total videos
                cursor = conn.execute("SELECT COUNT(*) FROM youtube_videos")
                total_videos = cursor.fetchone()[0]
                
                # Videos with transcripts
                cursor = conn.execute("SELECT COUNT(*) FROM youtube_videos WHERE transcript_path IS NOT NULL")
                videos_with_transcripts = cursor.fetchone()[0]
                
                # LLM processed videos
                cursor = conn.execute("SELECT COUNT(*) FROM youtube_videos WHERE llm_processed = TRUE")
                llm_processed = cursor.fetchone()[0]
                
                # Unique channels
                cursor = conn.execute("SELECT COUNT(DISTINCT channel_url) FROM youtube_videos")
                unique_channels = cursor.fetchone()[0]
                
                return {
                    'total_videos': total_videos,
                    'videos_with_transcripts': videos_with_transcripts,
                    'llm_processed': llm_processed,
                    'unprocessed': videos_with_transcripts - llm_processed,
                    'unique_channels': unique_channels
                }
                
        except Exception as e:
            self.logger.error(f"Error getting database stats: {str(e)}")
            return {}
    
    def get_unsummarized_videos(self, channel_url: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get videos that haven't been processed for summaries yet.
        
        Args:
            channel_url: Optional channel URL to filter by
            limit: Maximum number of videos to return
            
        Returns:
            List of unsummarized video dictionaries
        """
        try:
            with self.db_manager.get_connection() as conn:
                query = """
                    SELECT * FROM youtube_videos 
                    WHERE summary_processed = FALSE AND transcript_path IS NOT NULL
                """
                params = []
                
                if channel_url:
                    query += " AND channel_url = ?"
                    params.append(channel_url)
                
                query += " ORDER BY created_at ASC"
                
                if limit:
                    query += " LIMIT ?"
                    params.append(limit)
                
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Error getting unsummarized videos: {str(e)}")
            return []
    
    def mark_summary_processed(self, video_url: str, summary_text: str, audio_path: Optional[str] = None) -> bool:
        """
        Mark a video as summary processed.
        
        Args:
            video_url: YouTube video URL
            summary_text: The generated summary text
            audio_path: Optional path to audio file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_manager.get_connection() as conn:
                conn.execute(
                    """UPDATE youtube_videos 
                       SET summary_processed = ?, summary_text = ?, summary_audio_path = ?,
                           summary_processed_at = ?, summary_error = NULL, updated_at = ?
                       WHERE url = ?""",
                    (True, summary_text, audio_path, 
                     datetime.now(timezone.utc).isoformat(),
                     datetime.now(timezone.utc).isoformat(), video_url)
                )
                conn.commit()
                self.logger.debug(f"Marked video as summary processed: {video_url}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error marking video as summary processed: {str(e)}")
            return False
    
    def mark_summary_error(self, video_url: str, error_message: str) -> bool:
        """
        Mark a video summary processing as failed with error.
        
        Args:
            video_url: YouTube video URL
            error_message: Error message to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_manager.get_connection() as conn:
                conn.execute(
                    """UPDATE youtube_videos 
                       SET summary_error = ?, updated_at = ?
                       WHERE url = ?""",
                    (error_message, datetime.now(timezone.utc).isoformat(), video_url)
                )
                conn.commit()
                self.logger.debug(f"Marked video summary error: {video_url}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error marking video summary error: {str(e)}")
            return False
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Get statistics about summary processing.
        
        Returns:
            Dictionary containing summary statistics
        """
        try:
            with self.db_manager.get_connection() as conn:
                # Total videos with transcripts
                cursor = conn.execute("SELECT COUNT(*) FROM youtube_videos WHERE transcript_path IS NOT NULL")
                total_with_transcripts = cursor.fetchone()[0]
                
                # Summary processed videos
                cursor = conn.execute("SELECT COUNT(*) FROM youtube_videos WHERE summary_processed = TRUE")
                summary_processed = cursor.fetchone()[0]
                
                # Videos with summary errors
                cursor = conn.execute("SELECT COUNT(*) FROM youtube_videos WHERE summary_error IS NOT NULL")
                summary_errors = cursor.fetchone()[0]
                
                # Pending summaries
                pending = total_with_transcripts - summary_processed
                
                return {
                    'total_with_transcripts': total_with_transcripts,
                    'summary_processed': summary_processed,
                    'pending_summaries': pending,
                    'summary_errors': summary_errors
                }
                
        except Exception as e:
            self.logger.error(f"Error getting summary stats: {str(e)}")
            return {}
    
    def get_failed_summaries(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get videos that failed summary processing.
        
        Args:
            limit: Maximum number of videos to return
            
        Returns:
            List of failed summary video dictionaries
        """
        try:
            with self.db_manager.get_connection() as conn:
                query = """
                    SELECT * FROM youtube_videos 
                    WHERE summary_error IS NOT NULL AND transcript_path IS NOT NULL
                    ORDER BY updated_at DESC
                """
                params = []
                
                if limit:
                    query += " LIMIT ?"
                    params.append(limit)
                
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Error getting failed summaries: {str(e)}")
            return []