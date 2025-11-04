"""YouTube transcript fetching functionality."""

import yt_dlp
import json
import tempfile
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path

from src.time_reclamation.infrastructure import get_logger


class YouTubeTranscriptFetcher:
    """Handles fetching transcripts from YouTube videos."""
    
    def __init__(self):
        """Initialize the transcript fetcher."""
        self.logger = get_logger()
    
    def get_latest_videos(self, channel_url: str, max_videos: int = 5) -> List[Dict[str, Any]]:
        """
        Get latest videos from a channel with detailed information.
        
        Args:
            channel_url: Channel URL
            max_videos: Number of latest videos to retrieve
        
        Returns:
            List of video dictionaries with metadata
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',  # Fast extraction
            'playlistend': max_videos,
        }
        
        if not channel_url.endswith('/videos'):
            channel_url = f"{channel_url}/videos"
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(channel_url, download=False)
                
                videos = []
                if info and 'entries' in info:
                    for entry in info['entries'][:max_videos]:
                        if entry:
                            video_data = {
                                'id': entry.get('id'),
                                'url': f"https://www.youtube.com/watch?v={entry.get('id')}",
                                'title': entry.get('title'),
                                'channel_url': channel_url.replace('/videos', ''),
                                'fetched_at': datetime.now(timezone.utc).isoformat()
                            }
                            videos.append(video_data)
                
                self.logger.info(f"Found {len(videos)} latest videos from channel")
                return videos
                
        except Exception as e:
            self.logger.error(f"Error fetching latest videos: {str(e)}")
            return []
    
    def get_video_transcript(self, video_url: str, language: str = 'en') -> Optional[Dict[str, Any]]:
        """
        Get transcript from a YouTube video URL.
        
        Args:
            video_url: YouTube video URL
            language: Language code for transcript
        
        Returns:
            Dictionary containing transcript data with 'text', 'entries', and 'metadata'
            Returns None if no transcript is available
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': [language],
            'skip_download': True,
            'subtitlesformat': 'json3',
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract video info to get available subtitles
                info = ydl.extract_info(video_url, download=False)
                
                if not info:
                    self.logger.warning(f"Could not extract video info for {video_url}")
                    return None
                
                # Check for available subtitles
                subtitles = info.get('subtitles', {})
                automatic_captions = info.get('automatic_captions', {})
                
                # Try to get manual subtitles first, then automatic captions
                transcript_data = None
                source_type = None
                available_languages = []
                
                # Collect all available languages
                available_languages.extend(list(subtitles.keys()))
                available_languages.extend(list(automatic_captions.keys()))
                
                if language in subtitles:
                    transcript_data = subtitles[language]
                    source_type = 'manual'
                elif language in automatic_captions:
                    transcript_data = automatic_captions[language]
                    source_type = 'automatic'
                elif 'en' in subtitles and language != 'en':
                    transcript_data = subtitles['en']
                    source_type = 'manual'
                    language = 'en'
                elif 'en' in automatic_captions and language != 'en':
                    transcript_data = automatic_captions['en']
                    source_type = 'automatic'
                    language = 'en'
                else:
                    # Try first available language
                    if subtitles:
                        first_lang = list(subtitles.keys())[0]
                        transcript_data = subtitles[first_lang]
                        source_type = 'manual'
                        language = first_lang
                    elif automatic_captions:
                        first_lang = list(automatic_captions.keys())[0]
                        transcript_data = automatic_captions[first_lang]
                        source_type = 'automatic'
                        language = first_lang
                
                if not transcript_data:
                    self.logger.warning(f"No transcripts available for {video_url}")
                    return {
                        'text': None,
                        'entries': [],
                        'metadata': {
                            'video_id': info.get('id'),
                            'title': info.get('title'),
                            'error': 'No transcripts available',
                            'available_languages': list(set(available_languages)),
                            'fetched_at': datetime.now(timezone.utc).isoformat()
                        }
                    }
                
                # Use yt-dlp's built-in subtitle extraction
                with tempfile.TemporaryDirectory() as temp_dir:
                    subtitle_opts = {
                        'quiet': True,
                        'no_warnings': True,
                        'writesubtitles': True,
                        'writeautomaticsub': True,
                        'subtitleslangs': [language],
                        'skip_download': True,
                        'subtitlesformat': 'json3',
                        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                    }
                    
                    try:
                        with yt_dlp.YoutubeDL(subtitle_opts) as subtitle_ydl:
                            subtitle_ydl.download([video_url])
                            
                            # Find the downloaded subtitle file
                            subtitle_file = None
                            for file in os.listdir(temp_dir):
                                if file.endswith(f'.{language}.json3'):
                                    subtitle_file = os.path.join(temp_dir, file)
                                    break
                            
                            if not subtitle_file:
                                # Try any json3 file
                                for file in os.listdir(temp_dir):
                                    if file.endswith('.json3'):
                                        subtitle_file = os.path.join(temp_dir, file)
                                        break
                            
                            if subtitle_file and os.path.exists(subtitle_file):
                                with open(subtitle_file, 'r', encoding='utf-8') as f:
                                    transcript_json = json.load(f)
                                    
                                events = transcript_json.get('events', [])
                                transcript_entries = []
                                full_text = []
                                
                                for event in events:
                                    if 'segs' in event:
                                        start_time = event.get('tStartMs', 0) / 1000.0
                                        duration = event.get('dDurationMs', 0) / 1000.0
                                        
                                        text_segments = []
                                        for seg in event['segs']:
                                            if 'utf8' in seg:
                                                text_segments.append(seg['utf8'])
                                        
                                        if text_segments:
                                            text = ''.join(text_segments).strip()
                                            if text and text != '\n':
                                                transcript_entries.append({
                                                    'start': start_time,
                                                    'duration': duration,
                                                    'text': text
                                                })
                                                full_text.append(text)
                                
                                self.logger.info(f"Successfully extracted transcript with {len(transcript_entries)} entries")
                                return {
                                    'text': ' '.join(full_text),
                                    'entries': transcript_entries,
                                    'metadata': {
                                        'video_id': info.get('id'),
                                        'title': info.get('title'),
                                        'language': language,
                                        'source_type': source_type,
                                        'total_entries': len(transcript_entries),
                                        'available_languages': list(set(available_languages)),
                                        'fetched_at': datetime.now(timezone.utc).isoformat()
                                    }
                                }
                            
                    except Exception as e:
                        self.logger.error(f"Error downloading subtitle file: {e}")
                        
                # Fallback: return error info
                return {
                    'text': None,
                    'entries': [],
                    'metadata': {
                        'video_id': info.get('id'),
                        'title': info.get('title'),
                        'error': 'Could not extract transcript',
                        'available_languages': list(set(available_languages)),
                        'fetched_at': datetime.now(timezone.utc).isoformat()
                    }
                }
                    
        except Exception as e:
            self.logger.error(f"Error extracting transcript: {e}")
            return None