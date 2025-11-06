# Summary System Architecture

## Overview

The Summary System processes YouTube video transcripts, converts them to audio summaries using LLM and TTS, and delivers them via notifications. The workflow follows: **Fetch Transcript → LLM Summary → TTS Audio → Notify User → Cleanup**.

## Configuration Schema

### Channel Configuration Extension

Add optional `summary` section to channel configuration in `config.yml`:

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
        
        # Summary configuration (optional)
        summary:
          enabled: true  # Enable summary processing for this channel
          llm_provider: "claude_assistant"  # Optional: specific LLM instance
          tts_provider: "kokoro_english"    # Optional: specific TTS instance
          notification_provider: "personal_bot"  # Optional: specific notification instance
          system_prompt: |  # Optional: custom system prompt for summaries
            You are a podcast host creating an engaging audio summary.
            Convert the transcript into a conversational, easy-to-listen format.
            Focus on key insights and make it sound natural for audio playback.
            Keep it concise but informative (3-5 minutes when spoken).
```

### Default Behavior

When optional fields are missing:
- `llm_provider`: Auto-select first available LLM instance
- `tts_provider`: Auto-select first available TTS instance
- `notification_provider`: Auto-select first available notification instance
- `system_prompt`: Use default conversational podcast-style prompt

## Database Schema

### Updated youtube_videos Table

```sql
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
    
    -- Summary processing tracking
    summary_processed BOOLEAN DEFAULT FALSE,
    summary_text TEXT,  -- Store the LLM-generated summary
    summary_audio_path TEXT,  -- Temporary path (deleted after notification)
    summary_processed_at TIMESTAMP,
    summary_error TEXT,  -- Store any error messages
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fetched_at TEXT
)
```

### New Database Methods

```python
# In YouTubeDatabase class
def get_unsummarized_videos(self, channel_url: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]
def mark_summary_processed(self, video_url: str, summary_text: str, audio_path: Optional[str] = None) -> bool
def mark_summary_error(self, video_url: str, error_message: str) -> bool
def get_summary_stats(self) -> Dict[str, Any]
def get_failed_summaries(self, limit: Optional[int] = None) -> List[Dict[str, Any]]
```

## System Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Summary Command                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     SummaryService                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ • process_channel_summaries()                        │  │
│  │ • process_video_summary()                            │  │
│  │ • get_summary_stats()                                │  │
│  │ • retry_failed_summaries()                           │  │
│  │ • cleanup_audio_files()                              │  │
│  └──────────────────────────────────────────────────────┘  │
└───┬────────┬────────┬────────┬────────┬────────────────────┘
    │        │        │        │        │
    ▼        ▼        ▼        ▼        ▼
┌────────┐ ┌────┐ ┌─────┐ ┌─────┐ ┌──────────┐
│YouTube │ │LLM │ │ TTS │ │Notif│ │  Cache   │
│Database│ │Mgr │ │ Mgr │ │ Mgr │ │ Manager  │
└────────┘ └────┘ └─────┘ └─────┘ └──────────┘
```

### Workflow Sequence

```
1. Get Unprocessed Videos
   └─> Query database for videos with summary_processed = FALSE
   
2. For Each Video:
   a. Load Transcript
      └─> CacheManager.load_transcript_by_path()
   
   b. Get Channel Config
      └─> ConfigManager.get_channel_summary_config()
   
   c. Generate Summary
      └─> LLMManager.generate_response(system_prompt, transcript)
   
   d. Convert to Audio
      └─> TTSManager.generate_speech(summary_text, filename)
   
   e. Send Notification
      └─> NotificationManager.send_message(title + audio_file)
   
   f. Mark as Processed
      └─> Database.mark_summary_processed()
   
   g. Cleanup Audio File
      └─> os.remove(audio_path)
```

## File Structure

### New Files

```
src/time_reclamation/core/youtube/
├── summary_service.py          # Main summary orchestration service

src/time_reclamation/interfaces/cli/commands/
├── summary.py                  # CLI command implementation

cache_data/
└── summaries/
    └── audio/                  # Temporary audio files
```

### Modified Files

```
src/time_reclamation/core/youtube/
├── database.py                 # Add summary-related methods
├── service.py                  # Integrate summary service
└── __init__.py                 # Export summary service

src/time_reclamation/config/
└── manager.py                  # Parse summary configuration

src/time_reclamation/interfaces/cli/commands/
└── __init__.py                 # Register summary command
```

## Implementation Details

### SummaryService Class

```python
class SummaryService:
    """Service for processing video summaries."""
    
    def __init__(self):
        self.logger = get_logger()
        self.database = YouTubeDatabase()
        self.cache_manager = YouTubeCacheManager()
        self.llm_manager = get_llm_manager()
        self.tts_manager = get_tts_manager()
        self.notification_manager = get_notification_manager()
        self.config_manager = get_config_manager()
        self.audio_dir = Path("cache_data/summaries/audio")
        self.audio_dir.mkdir(parents=True, exist_ok=True)
    
    def process_channel_summaries(
        self, 
        channel_name: Optional[str] = None,
        limit: Optional[int] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """Process summaries for channel(s)."""
        
    def process_video_summary(
        self,
        video_url: str,
        channel_config: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Process summary for a single video."""
        
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary processing statistics."""
        
    def retry_failed_summaries(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Retry videos that failed summary processing."""
        
    def cleanup_audio_files(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """Clean up orphaned audio files."""
```

### LLM System Prompt

**Default Conversational Podcast-Style Prompt:**

```
You are a podcast host creating an engaging audio summary of a YouTube video transcript.

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

Important: Output ONLY the summary text, no meta-commentary or explanations.
```

### Audio File Management

**Naming Convention:**
```
summary_{video_id}_{timestamp}.wav
```

**Storage Location:**
```
cache_data/summaries/audio/
```

**Lifecycle:**
1. Created during TTS conversion
2. Sent via notification
3. Deleted immediately after successful notification
4. Kept on error for retry (with error logged in database)
5. Cleanup command removes files older than 24 hours

### Notification Format

**Text Message:**
```
🎥 New Video Summary: {video_title}

Channel: {channel_name}
Duration: ~{estimated_minutes} minutes

[Audio file attached]
```

**Telegram Implementation:**
- Use `send_audio()` method with audio file
- Set `title` metadata to video title
- Set `performer` metadata to channel name

## CLI Command Interface

### Command: `summary`

```bash
# Process summaries for all enabled channels
python -m time_reclamation summary process

# Process specific channel
python -m time_reclamation summary process "TechWizard9000"

# Process specific video by URL
python -m time_reclamation summary process --video "https://youtube.com/watch?v=..."

# Process with limit
python -m time_reclamation summary process --limit 5

# Force reprocess (even if already processed)
python -m time_reclamation summary process --force

# Show summary processing status
python -m time_reclamation summary status

# Show status for specific channel
python -m time_reclamation summary status "TechWizard9000"

# Retry failed summaries
python -m time_reclamation summary retry

# Retry with limit
python -m time_reclamation summary retry --limit 3

# Cleanup orphaned audio files
python -m time_reclamation summary cleanup

# Cleanup with custom age threshold
python -m time_reclamation summary cleanup --max-age 48

# Show help
python -m time_reclamation summary --help
```

### Subcommands

1. **process** - Process video summaries
   - Optional: channel name
   - Flags: `--video URL`, `--limit N`, `--force`

2. **status** - Show summary processing statistics
   - Optional: channel name
   - Shows: total videos, processed, pending, failed

3. **retry** - Retry failed summaries
   - Flags: `--limit N`

4. **cleanup** - Remove orphaned audio files
   - Flags: `--max-age HOURS` (default: 24)

## Error Handling

### Error Types and Responses

| Error Type | Action | Retry |
|------------|--------|-------|
| Transcript not found | Skip, log warning | No |
| LLM generation failed | Store error, keep transcript | Yes |
| TTS conversion failed | Store error, keep summary | Yes |
| Notification failed | Store error, keep audio | Yes |
| Configuration missing | Use defaults or skip | No |

### Error Storage

Errors are stored in the `summary_error` column:

```json
{
  "error_type": "llm_generation_failed",
  "error_message": "API rate limit exceeded",
  "timestamp": "2025-11-06T21:00:00Z",
  "retry_count": 1
}
```

### Retry Logic

- Maximum 3 retry attempts per video
- Exponential backoff between retries
- Clear error after successful processing

## Integration Points

### With Existing Systems

1. **YouTubeService**
   - Get unprocessed videos via `get_unprocessed_videos()`
   - Access channel configuration

2. **CacheManager**
   - Load transcripts via `load_transcript_by_path()`

3. **LLMManager**
   - Generate summaries via `generate_response()`
   - Support custom system prompts

4. **TTSManager**
   - Convert text to audio via `generate_speech()`
   - Handle multiple TTS providers

5. **NotificationManager**
   - Send messages with audio attachments
   - Support multiple notification providers

## Configuration Manager Updates

### New Methods

```python
class ConfigManager:
    def get_channel_summary_config(self, channel_name: str) -> Optional[Dict[str, Any]]:
        """Get summary configuration for a specific channel."""
        
    def get_summary_enabled_channels(self) -> List[str]:
        """Get list of channels with summary enabled."""
```

## Testing Strategy

### Unit Tests

1. **SummaryService Tests**
   - Test video processing workflow
   - Test error handling
   - Test cleanup logic

2. **Database Tests**
   - Test summary tracking methods
   - Test query methods

3. **Configuration Tests**
   - Test summary config parsing
   - Test default value handling

### Integration Tests

1. **End-to-End Workflow**
   - Mock LLM, TTS, and Notification providers
   - Test complete summary pipeline
   - Verify cleanup after success

2. **Error Scenarios**
   - Test retry logic
   - Test error storage
   - Test partial failures

## Performance Considerations

1. **Batch Processing**
   - Process multiple videos in sequence
   - Limit concurrent operations to avoid rate limits

2. **Resource Management**
   - Clean up audio files immediately after use
   - Monitor disk space in audio directory

3. **Rate Limiting**
   - Respect LLM provider rate limits
   - Add delays between API calls if needed

## Security Considerations

1. **File System**
   - Sanitize filenames
   - Restrict audio directory permissions
   - Validate file paths

2. **API Keys**
   - Use existing secure configuration system
   - Never log API keys or tokens

3. **Content Validation**
   - Validate transcript content before processing
   - Sanitize summary text before TTS conversion

## Future Enhancements

1. **Scheduling**
   - Cron-like scheduling for automatic processing
   - Time-based triggers

2. **Customization**
   - Per-video custom prompts
   - Multiple summary formats (short/long)

3. **Analytics**
   - Track processing times
   - Monitor success rates
   - Generate reports

4. **Multi-language Support**
   - Language-specific TTS voices
   - Translation capabilities

5. **Advanced Features**
   - Summary caching
   - Incremental updates
   - Batch notifications