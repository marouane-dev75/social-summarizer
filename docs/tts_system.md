# TTS (Text-to-Speech) System

## Overview

The TTS system provides a flexible, extensible framework for generating speech from text using various TTS providers. It follows the same architectural patterns as the LLM system, allowing multiple provider instances with different configurations.

## Features

- **Multiple Provider Support**: Configure multiple TTS instances with different voices and settings
- **Provider Abstraction**: Easy to add new TTS providers (Kokoro, Coqui, etc.)
- **Instance Management**: Each instance has its own configuration and can be selected at runtime
- **Automatic Filename Generation**: Timestamp-based filenames if not specified
- **Audio Chunking**: Automatically combines audio chunks into single output files
- **CLI Integration**: Simple command-line interface for generating speech

## Architecture

### Components

1. **TTSProvider Interface** ([`interface.py`](../src/time_reclamation/infrastructure/tts/interface.py))
   - Abstract base class defining the TTS provider contract
   - Methods: `generate_speech()`, `is_configured()`, `test_connection()`, `cleanup()`

2. **TTSManager** ([`manager.py`](../src/time_reclamation/infrastructure/tts/manager.py))
   - Manages multiple TTS provider instances
   - Handles provider selection and initialization
   - Provides high-level API for speech generation

3. **Kokoro Provider** ([`providers/kokoro.py`](../src/time_reclamation/infrastructure/tts/providers/kokoro.py))
   - Implementation for Kokoro-82M TTS model
   - Supports multiple voices and languages
   - Lazy loading for efficient resource usage

4. **TTS Command** ([`commands/tts.py`](../src/time_reclamation/interfaces/cli/commands/tts.py))
   - CLI command for interacting with TTS system
   - Supports listing, testing, and generating speech

## Configuration

### Config File Structure

Add TTS configuration to [`config.yml`](../src/time_reclamation/config/config.yml):

```yaml
tts:
  providers:
    - name: "kokoro_english"
      type: "kokoro"
      enabled: true
      config:
        voice: "af_alloy"
        lang_code: "a"
        repo_id: "hexgrad/Kokoro-82M"
        sample_rate: 24000
        output_dir: "cache_data/tts"
```

### Configuration Parameters

#### Kokoro Provider

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `voice` | string | Yes | - | Voice to use (af_alloy, af_heart, etc.) |
| `lang_code` | string | Yes | - | Language code (a=American, b=British) |
| `repo_id` | string | No | hexgrad/Kokoro-82M | Hugging Face repository |
| `sample_rate` | integer | No | 24000 | Audio sample rate in Hz |
| `output_dir` | string | No | cache_data/tts | Output directory for audio files |

### Available Voices

Kokoro TTS supports multiple voices:

- **Female American**: `af_alloy`, `af_bella`, `af_nicole`, `af_sarah`, `af_heart`
- **Male American**: `am_adam`, `am_michael`
- **Female British**: `bf_emma`, `bf_isabella`
- **Male British**: `bm_george`, `bm_lewis`

### Language Codes

- `a` - American English
- `b` - British English

## Usage

### Command Line Interface

#### List Available Instances

```bash
python main.py tts --list
```

#### Test TTS Providers

```bash
# Test all providers
python main.py tts --test

# Test specific provider
python main.py tts --test kokoro_english
```

#### Generate Speech

```bash
# Basic usage (auto-generates filename)
python main.py tts --text "Hello, world!"

# Specify output filename
python main.py tts --text "Hello, world!" --output greeting.wav

# Use specific instance
python main.py tts kokoro_english --text "This is a test"

# Using aliases
python main.py speak --text "Using the speak alias"
python main.py voice --text "Using the voice alias"
```

### Python API

```python
from src.time_reclamation.infrastructure.tts import get_tts_manager, generate_speech

# Using the manager
tts_manager = get_tts_manager()

# Generate speech with auto-selected instance
result = tts_manager.generate_speech(
    text="Hello, world!",
    output_filename="greeting.wav"
)

# Generate speech with specific instance
result = tts_manager.generate_speech(
    text="Hello, world!",
    output_filename="greeting.wav",
    instance_name="kokoro_english"
)

# Check result
if result.status == TTSStatus.SUCCESS:
    print(f"Audio saved to: {result.output_file}")
    print(f"Duration: {result.audio_duration:.2f}s")
    print(f"Generation time: {result.generation_time:.2f}s")
else:
    print(f"Error: {result.error_details}")

# Convenience function
result = generate_speech("Hello, world!", "greeting.wav")
```

## Output Files

### File Location

Audio files are saved to the configured output directory (default: `cache_data/tts/`).

### File Naming

- **User-specified**: Use the provided filename (e.g., `greeting.wav`)
- **Auto-generated**: Timestamp-based format `tts_YYYYMMDD_HHMMSS.wav`

### File Format

- **Format**: WAV (uncompressed)
- **Sample Rate**: 24000 Hz (configurable)
- **Channels**: Mono or stereo (depends on model)

## Adding New TTS Providers

To add a new TTS provider:

1. **Create Provider Class**

Create a new file in [`providers/`](../src/time_reclamation/infrastructure/tts/providers/):

```python
from ..interface import TTSProvider, TTSResult, TTSStatus

class MyTTSProvider(TTSProvider):
    def __init__(self, instance_name: str, config: Dict[str, Any]):
        self.instance_name = instance_name
        # Initialize from config
    
    @property
    def provider_name(self) -> str:
        return f"MyTTS ({self.instance_name})"
    
    def is_configured(self) -> bool:
        # Check if properly configured
        pass
    
    def generate_speech(self, text: str, output_filename: str) -> TTSResult:
        # Generate speech implementation
        pass
    
    def test_connection(self) -> TTSResult:
        # Test implementation
        pass
    
    def cleanup(self) -> None:
        # Cleanup resources
        pass
```

2. **Register Provider**

Add to [`manager.py`](../src/time_reclamation/infrastructure/tts/manager.py):

```python
from .providers.mytts import MyTTSProvider

# In _initialize_providers method:
elif provider_type == "mytts":
    provider = MyTTSProvider(instance_name, config_dict)
```

3. **Add Configuration Validation**

Add to [`config/manager.py`](../src/time_reclamation/config/manager.py):

```python
def _validate_mytts_config(self, instance_name: str, config: Dict[str, Any]) -> List[str]:
    errors = []
    # Add validation logic
    return errors
```

4. **Update Configuration**

Add example to [`config.yml`](../src/time_reclamation/config/config.yml):

```yaml
- name: "mytts_instance"
  type: "mytts"
  enabled: false
  config:
    # Provider-specific config
```

## Error Handling

### Common Errors

1. **Provider Not Configured**
   - Error: "TTS provider instance is not properly configured"
   - Solution: Check configuration in `config.yml` and ensure all required fields are set

2. **Missing Dependencies**
   - Error: "kokoro is not installed"
   - Solution: Install dependencies with `pip install -r requirements.txt`

3. **Empty Text**
   - Error: "Text cannot be empty"
   - Solution: Provide non-empty text to convert to speech

4. **Output Directory Issues**
   - Error: "Failed to create output directory"
   - Solution: Check directory permissions and disk space

### Debugging

Enable debug logging:

```bash
python main.py tts --text "Hello" --debug
```

## Performance Considerations

### Model Loading

- Models are lazy-loaded on first use
- Loading time varies by model size (typically 1-5 seconds for Kokoro)
- Models remain in memory for subsequent requests

### Generation Speed

- Kokoro-82M: ~0.5-2 seconds for short texts
- Speed depends on text length and hardware
- GPU acceleration available (configure `gpu_layers` if using LlamaCpp-style models)

### Memory Usage

- Kokoro-82M: ~300MB RAM
- Audio chunks are combined in memory before saving
- Consider memory constraints for very long texts

## Best Practices

1. **Instance Naming**: Use descriptive names (e.g., `kokoro_narrator`, `kokoro_british`)
2. **Voice Selection**: Test different voices to find the best fit for your use case
3. **Output Organization**: Use subdirectories in `output_dir` for different projects
4. **Error Handling**: Always check `TTSResult.status` before using output
5. **Resource Cleanup**: Call `cleanup_all()` when done with TTS manager

## Troubleshooting

### Audio Quality Issues

- Check sample rate configuration
- Ensure text is properly formatted (no special characters that might cause issues)
- Try different voices

### Generation Failures

- Verify all dependencies are installed
- Check available disk space
- Ensure output directory is writable
- Review logs for detailed error messages

### Performance Issues

- Consider using GPU acceleration if available
- Reduce text length for faster generation
- Use appropriate sample rate (lower = faster but lower quality)

## Examples

### Basic Text-to-Speech

```bash
python main.py tts --text "Welcome to the Time Reclamation application."
```

### Multiple Sentences

```bash
python main.py tts --text "This is the first sentence. This is the second sentence. And this is the third."
```

### Long-Form Content

```bash
python main.py tts --text "$(cat article.txt)" --output article_audio.wav
```

### Batch Processing

```python
from src.time_reclamation.infrastructure.tts import get_tts_manager

tts_manager = get_tts_manager()

texts = [
    "First paragraph of content.",
    "Second paragraph of content.",
    "Third paragraph of content."
]

for i, text in enumerate(texts):
    result = tts_manager.generate_speech(
        text=text,
        output_filename=f"paragraph_{i+1}.wav"
    )
    if result.status == TTSStatus.SUCCESS:
        print(f"Generated: {result.output_file}")
```

## Future Enhancements

- Support for additional TTS providers (Coqui, ElevenLabs, Google Cloud TTS, Azure TTS)
- Audio format conversion (MP3, OGG)
- SSML support for advanced speech control
- Speed and pitch adjustment
- Batch processing optimization
- Audio normalization and post-processing
- Cache management and deduplication

## References

- [Kokoro TTS on Hugging Face](https://huggingface.co/hexgrad/Kokoro-82M)
- [Architecture Documentation](tts_system_architecture.md)
- [Configuration Guide](../src/time_reclamation/config/config.yml)