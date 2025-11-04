# YouTube Transcript Scraping System

## Overview

The YouTube transcript scraping system is a comprehensive solution for automatically fetching, caching, and managing YouTube video transcripts from multiple channels. It provides duplicate detection, database tracking, and CLI management tools.

## Architecture

### Core Components

1. **YouTubeService** - Main orchestrator service
2. **YouTubeTranscriptFetcher** - Handles video transcript extraction using yt-dlp
3. **YouTubeChannelManager** - Manages multiple channel configurations
4. **YouTubeDatabase** - Database operations for tracking videos and transcripts
5. **YouTubeCacheManager** - File system caching for transcript storage

### Database Schema

The system uses a SQLite table `youtube_videos` with the following structure:

```sql
CREATE TABLE youtube_videos (
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
    llm_processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fetched_at TEXT
);
```

## Configuration

### Channel Configuration

Add YouTube channels to your `config.yml`:

```yaml
platforms:
  youtube:
    enabled: true
    channels:
      - name: "TechWizard9000"
        scrap: true
        url: "https://www.youtube.com/@TechWizard9000"
        max_videos: 10
        language: "fr"
        cache_folder: "cache_data/youtube_transcripts/TechWizard9000"
      - name: "Another Channel"
        scrap: true
        url: "https://www.youtube.com/@anotherchannel"
        max_videos: 5
        language: "en"
        cache_folder: "cache_data/youtube_transcripts/another_channel"
```

### Configuration Parameters

- **name**: Human-readable channel name
- **scrap**: Enable/disable scraping for this channel
- **url**: YouTube channel URL
- **max_videos**: Maximum number of latest videos to fetch
- **language**: Preferred transcript language (e.g., "en", "fr", "es")
- **cache_folder**: Relative path for storing transcript files

## CLI Usage

### Basic Commands

```bash
# Scrape all configured channels
python main.py youtube scrape

# Scrape a specific channel
python main.py youtube scrape "TechWizard9000"

# Force refresh (ignore cache)
python main.py youtube scrape --force

# Show statistics
python main.py youtube stats

# List configured channels
python main.py youtube channels

# Get transcript for specific video
python main.py youtube video "https://www.youtube.com/watch?v=VIDEO_ID"

# Get transcript in specific language
python main.py youtube video "https://www.youtube.com/watch?v=VIDEO_ID" "fr"

# Show unprocessed videos
python main.py youtube unprocessed

# Show limited number of unprocessed videos
python main.py youtube unprocessed 10

# Mark video as LLM processed
python main.py youtube mark-processed "https://www.youtube.com/watch?v=VIDEO_ID"

# Show cache statistics
python main.py youtube cache-stats

# Clean up empty cache directories
python main.py youtube cleanup

# Show help
python main.py youtube help
```

### Advanced Usage

```bash
# Show full transcript (not just preview)
python main.py youtube video "https://www.youtube.com/watch?v=VIDEO_ID" --full

# Debug mode for detailed logging
python main.py youtube scrape --debug
```

## Programmatic Usage

### Basic Service Usage

```python
from src.time_reclamation.core.youtube import get_youtube_service

# Get the YouTube service
youtube_service = get_youtube_service()

# Scrape all channels
results = youtube_service.scrape_all_channels()

# Scrape specific channel
results = youtube_service.scrape_channel("TechWizard9000")

# Get transcript for specific video
transcript = youtube_service.get_video_transcript(
    "https://www.youtube.com/watch?v=VIDEO_ID", 
    language="fr"
)

# Get statistics
stats = youtube_service.get_database_stats()
channel_stats = youtube_service.get_channel_stats()

# Get unprocessed videos
unprocessed = youtube_service.get_unprocessed_videos(limit=10)

# Mark video as processed
youtube_service.mark_video_processed("https://www.youtube.com/watch?v=VIDEO_ID")
```

### Working with Individual Components

```python
from src.time_reclamation.core.youtube import (
    YouTubeTranscriptFetcher,
    YouTubeDatabase,
    YouTubeCacheManager,
    YouTubeChannelManager
)

# Direct transcript fetching
fetcher = YouTubeTranscriptFetcher()
videos = fetcher.get_latest_videos("https://www.youtube.com/@channel", max_videos=5)
transcript = fetcher.get_video_transcript("https://www.youtube.com/watch?v=VIDEO_ID", "en")

# Database operations
db = YouTubeDatabase()
video_exists = db.video_exists("https://www.youtube.com/watch?v=VIDEO_ID")
video_info = db.get_video_by_url("https://www.youtube.com/watch?v=VIDEO_ID")

# Cache management
cache = YouTubeCacheManager()
cache_exists = cache.transcript_exists("cache_folder", "video_id", "title")
transcript_data = cache.load_transcript("cache_folder", "video_id", "title")

# Channel management
channel_manager = YouTubeChannelManager()
channels = channel_manager.get_channels()
results = channel_manager.process_all_channels()
```

## Features

### Duplicate Detection

The system implements comprehensive duplicate detection:

1. **Database Check**: Verifies if video URL already exists in database
2. **File System Check**: Confirms transcript file exists in cache
3. **Smart Refresh**: Only fetches new transcripts when needed

### Caching Strategy

- **Hierarchical Storage**: Organized by channel-specific folders
- **JSON Format**: Structured storage with metadata
- **Filename Sanitization**: Safe filesystem naming
- **Automatic Cleanup**: Removes empty directories

### Error Handling

- **Graceful Degradation**: Continues processing other videos on individual failures
- **Comprehensive Logging**: Detailed error reporting and debugging
- **Retry Logic**: Built-in resilience for network issues
- **Validation**: Input validation and error recovery

### Language Support

- **Multi-language**: Supports any language available on YouTube
- **Fallback Strategy**: Falls back to English if preferred language unavailable
- **Auto-detection**: Uses first available language if none specified

## Transcript Data Structure

### Returned Transcript Format

```python
{
    'text': 'Full transcript text...',
    'entries': [
        {
            'start': 0.0,      # Start time in seconds
            'duration': 2.5,   # Duration in seconds
            'text': 'Hello...' # Text segment
        },
        # ... more entries
    ],
    'metadata': {
        'video_id': 'VIDEO_ID',
        'title': 'Video Title',
        'language': 'en',
        'source_type': 'automatic',  # or 'manual'
        'total_entries': 150,
        'available_languages': ['en', 'fr', 'es'],
        'fetched_at': '2024-01-01T12:00:00Z'
    }
}
```

### Cache File Structure

```python
{
    'cached_at': '2024-01-01T12:00:00Z',
    'video_id': 'VIDEO_ID',
    'title': 'Video Title',
    'cache_path': '/path/to/cache/file.json',
    'transcript': {
        # ... transcript data as above
    }
}
```

## Dependencies

- **yt-dlp**: YouTube video and subtitle extraction
- **sqlite3**: Database operations (built-in Python)
- **json**: Data serialization (built-in Python)
- **pathlib**: File system operations (built-in Python)

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure channels in `config.yml`

3. Initialize database (automatic on first run):
```bash
python main.py youtube stats
```

## Troubleshooting

### Common Issues

1. **No transcripts available**
   - Some videos don't have transcripts
   - Try different language codes
   - Check if video is public

2. **Permission errors**
   - Ensure write permissions for cache directories
   - Check database file permissions

3. **Network issues**
   - Verify internet connection
   - Some regions may block YouTube access
   - Consider using VPN if needed

4. **yt-dlp errors**
   - Update yt-dlp: `pip install --upgrade yt-dlp`
   - Some videos may be geo-blocked or private

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
python main.py youtube scrape --debug
```

### Log Files

Check application logs for detailed error information:
- Database operations
- Network requests
- File system operations
- Transcript processing

## Performance Considerations

### Optimization Tips

1. **Batch Processing**: Process multiple channels together
2. **Cache Utilization**: Leverage existing cached transcripts
3. **Selective Scraping**: Use `max_videos` to limit scope
4. **Cleanup**: Regularly clean up cache directories

### Resource Usage

- **Network**: Moderate bandwidth for video metadata and subtitles
- **Storage**: JSON files are typically 10-100KB per transcript
- **CPU**: Minimal processing overhead
- **Memory**: Low memory footprint

## Future Enhancements

### Planned Features

1. **LLM Integration**: Automatic transcript processing and summarization
2. **Webhook Support**: Real-time notifications for new transcripts
3. **Export Formats**: Support for various output formats (TXT, SRT, etc.)
4. **Scheduling**: Automated periodic scraping
5. **Analytics**: Advanced statistics and reporting

### Extension Points

The system is designed for extensibility:

- **Custom Processors**: Add transcript processing pipelines
- **Storage Backends**: Support for cloud storage
- **Notification Systems**: Integration with various messaging platforms
- **API Endpoints**: REST API for external integrations

## Contributing

When contributing to the YouTube system:

1. Follow existing code patterns and structure
2. Add comprehensive tests for new features
3. Update documentation for any changes
4. Ensure backward compatibility
5. Test with various YouTube channels and languages

## License

This YouTube transcript scraping system is part of the Time Reclamation App and follows the same licensing terms.