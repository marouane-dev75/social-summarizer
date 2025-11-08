# Time Reclamation App

Reclaim time wasted on social media by getting curated summaries instead of endless scrolling.

## ✨ Features

### 🎯 Smart Content Curation
- **YouTube Channel Monitoring**: Automatically track and fetch new videos from your favorite channels
- **Intelligent Transcript Extraction**: Extract video transcripts in multiple languages (English, French, etc.)
- **Configurable Video Limits**: Control how many videos to process per channel

### 🤖 AI-Powered Summarization
- **Multi-LLM Support**: Choose from various AI providers:
  - **Local Models**: LlamaCpp (GGUF models), Ollama (llama2, mistral, codellama, etc.)
  - **Cloud Providers**: Anthropic Claude (Haiku, Sonnet), OpenAI GPT (GPT-5, O4-mini)
- **Custom System Prompts**: Tailor summaries to your preferences (conversational, technical, brief, etc.)
- **Flexible Provider Selection**: Use different LLMs for different channels or content types

### 🔊 Text-to-Speech Integration
- **Multiple TTS Engines**:
  - **Kokoro TTS**: High-quality neural voices (American/British English, multiple voice options)
  - **Piper TTS**: Lightweight, fast synthesis with multi-language support
- **Audio Summary Generation**: Convert text summaries into audio files for on-the-go listening
- **Voice Customization**: Choose from various voices and accents

### 📱 Smart Notifications
- **Telegram Integration**: Receive summaries directly in your Telegram chat
- **Multi-Bot Support**: Configure multiple notification channels for different content types
- **Audio Delivery**: Get audio summaries sent directly to your messaging app

### 💾 Efficient Caching & State Management
- **Local Caching**: Store transcripts and summaries to avoid redundant processing
- **SQLite Database**: Track processed videos and maintain state across runs
- **Incremental Updates**: Only process new content since last run

### 🛠️ Developer-Friendly
- **CLI Interface**: Easy-to-use command-line tools for all operations
- **Modular Architecture**: Clean separation of concerns with pluggable providers
- **Extensible Design**: Easy to add new platforms, LLMs, or TTS providers
- **YAML Configuration**: Simple, human-readable configuration files

## 📋 Requirements

- Python 3.8+
- FFmpeg (for audio processing)
- Optional: CUDA-capable GPU for faster local LLM inference

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/marouane-dev75/social-summarizer
cd social-summarizer

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `config.local.yml` file based on the example below:

```yaml
# Platform Configuration
platforms:
  youtube:
    enabled: true
    channels:
      - name: "TechChannel"
        scrap: true
        url: "https://www.youtube.com/@TechChannel"
        max_videos: 5
        language: "en"
        cache_folder: "cache_data/youtube_transcripts/tech_channel"
        summary:
          enabled: true
          llm_provider: "ollama_local"
          tts_provider: "kokoro_english"
          notification_provider: "personal_bot"
          system_prompt: |
            You are a YouTube video summarizer that creates a single flowing 
            paragraph in plain text, using natural speech-friendly language 
            without formatting, symbols, or markdown, presenting the main 
            topic followed by key points with smooth transitions and ending 
            with a conclusion.

# Notification Configuration
notifications:
  providers:
    - name: "personal_bot"
      type: "telegram"
      enabled: true
      config:
        bot_token: "YOUR_BOT_TOKEN_HERE"  # Get from @BotFather on Telegram
        chat_id: "YOUR_CHAT_ID_HERE"      # Your Telegram chat ID
        timeout_seconds: 30
        retry_attempts: 3

# LLM Configuration
llm:
  providers:
    # Local Ollama instance
    - name: "ollama_local"
      type: "ollama"
      enabled: true
      config:
        base_url: "http://localhost:11434"
        model: "llama2"  # or mistral, codellama, etc.
        timeout_seconds: 120
        generation_config:
          temperature: 0.7
          num_predict: 4000
          top_p: 0.9
          top_k: 40
        default_system_prompt: "You are a helpful AI assistant."
    
    # Cloud provider example (optional)
    - name: "claude_assistant"
      type: "anthropic"
      enabled: false
      config:
        api_key: "YOUR_ANTHROPIC_API_KEY"
        model: "claude-haiku-4-5"
        max_tokens: 4000
        temperature: 0.7

# TTS Configuration
tts:
  providers:
    - name: "kokoro_english"
      type: "kokoro"
      enabled: true
      config:
        voice: "af_alloy"  # Available: af_heart, af_alloy, af_bella, am_adam, etc.
        lang_code: "a"     # a = American English, b = British English
        repo_id: "hexgrad/Kokoro-82M"
        sample_rate: 24000
        output_dir: "cache_data/tts"
    
    - name: "piper_french"
      type: "piper"
      enabled: false
      config:
        model_path: "/path/to/fr_FR-siwis-medium.onnx"
        output_dir: "cache_data/tts"
```

### Usage

```bash
# Process YouTube channels and generate summaries
python main.py youtube process

# Test LLM provider
python main.py llm test --provider ollama_local --prompt "Hello, how are you?"

# Test TTS provider
python main.py tts test --provider kokoro_english --text "This is a test."

# Test notification
python main.py notify test --provider personal_bot --message "Test notification"

# View database info
python main.py db info

# Show version
python main.py version
```

## 📁 Project Structure

```
TimeReclamation/
├── main.py                          # Application entry point
├── requirements.txt                 # Python dependencies
├── README.md                        # This file
│
├── src/time_reclamation/
│   ├── __init__.py                  # Package initialization
│   │
│   ├── config/                      # Configuration management
│   │   ├── __init__.py
│   │   ├── manager.py               # Config loader and validator
│   │   ├── config.yml               # Default configuration template
│   │   └── config.local.yml         # User-specific configuration (gitignored)
│   │
│   ├── core/                        # Core business logic
│   │   ├── __init__.py
│   │   └── youtube/                 # YouTube platform implementation
│   │       ├── __init__.py
│   │       ├── service.py           # Main YouTube service
│   │       ├── channel_manager.py   # Channel operations
│   │       ├── transcript_fetcher.py # Transcript extraction
│   │       ├── cache_manager.py     # Caching logic
│   │       ├── summary_service.py   # Summary generation
│   │       └── database.py          # YouTube-specific DB operations
│   │
│   ├── infrastructure/              # External integrations
│   │   ├── __init__.py
│   │   │
│   │   ├── llm/                     # LLM providers
│   │   │   ├── __init__.py
│   │   │   ├── interface.py         # LLM provider interface
│   │   │   ├── manager.py           # LLM provider manager
│   │   │   └── providers/
│   │   │       ├── __init__.py
│   │   │       ├── llamacpp.py      # LlamaCpp implementation
│   │   │       ├── anthropic.py     # Claude implementation
│   │   │       ├── openai.py        # OpenAI GPT implementation
│   │   │       └── ollama.py        # Ollama implementation
│   │   │
│   │   ├── tts/                     # Text-to-Speech providers
│   │   │   ├── __init__.py
│   │   │   ├── interface.py         # TTS provider interface
│   │   │   ├── manager.py           # TTS provider manager
│   │   │   └── providers/
│   │   │       ├── __init__.py
│   │   │       ├── kokoro.py        # Kokoro TTS implementation
│   │   │       └── piper.py         # Piper TTS implementation
│   │   │
│   │   ├── notifications/           # Notification providers
│   │   │   ├── __init__.py
│   │   │   ├── interface.py         # Notification provider interface
│   │   │   ├── manager.py           # Notification provider manager
│   │   │   └── providers/
│   │   │       ├── __init__.py
│   │   │       └── telegram.py      # Telegram implementation
│   │   │
│   │   ├── database/                # Database management
│   │   │   ├── __init__.py
│   │   │   └── manager.py           # SQLite database manager
│   │   │
│   │   └── logging/                 # Logging infrastructure
│   │       ├── __init__.py
│   │       └── logger.py            # Centralized logger
│   │
│   └── interfaces/                  # User interfaces
│       ├── __init__.py
│       └── cli/                     # Command-line interface
│           ├── __init__.py
│           ├── manager.py           # CLI manager
│           ├── command_pattern.py   # Command pattern implementation
│           └── commands/            # CLI commands
│               ├── __init__.py
│               ├── base.py          # Base command class
│               ├── youtube.py       # YouTube commands
│               ├── llm.py           # LLM commands
│               ├── tts.py           # TTS commands
│               ├── notify_test.py   # Notification test command
│               ├── summary.py       # Summary commands
│               ├── db_info.py       # Database info command
│               └── version.py       # Version command
│
├── docs/                            # Documentation
│   ├── llm_system.md                # LLM system documentation
│   ├── tts_system.md                # TTS system documentation
│   ├── youtube_system.md            # YouTube system documentation
│   └── summary_system.md            # Summary system documentation
│
└── cache_data/                      # Runtime data (gitignored)
    ├── youtube_transcripts/         # Cached transcripts
    ├── tts/                         # Generated audio files
    └── state.db                     # SQLite database
```

## 🏗️ Architecture

### Design Patterns

- **Provider Pattern**: Pluggable LLM, TTS, and notification providers
- **Command Pattern**: CLI commands with consistent interface
- **Manager Pattern**: Centralized management of providers and resources
- **Repository Pattern**: Database abstraction for state management

### Key Components

1. **Configuration Layer** ([`config/manager.py`](src/time_reclamation/config/manager.py:1))
   - YAML-based configuration with validation
   - Support for local overrides (config.local.yml)
   - Environment-specific settings

2. **Core Business Logic** ([`core/`](src/time_reclamation/core/))
   - Platform-specific implementations (YouTube, Reddit, Twitter)
   - Content extraction and processing
   - Summary generation orchestration

3. **Infrastructure Layer** ([`infrastructure/`](src/time_reclamation/infrastructure/))
   - LLM providers with unified interface
   - TTS engines for audio generation
   - Notification delivery systems
   - Database and logging utilities

4. **Interface Layer** ([`interfaces/cli/`](src/time_reclamation/interfaces/cli/))
   - Command-line interface with subcommands
   - User-friendly command structure
   - Error handling and feedback

## 🔧 Technical Stack

- **Language**: Python 3.8+
- **Configuration**: PyYAML
- **Database**: SQLite3
- **LLM Integration**: 
  - llama-cpp-python (local GGUF models)
  - anthropic (Claude API)
  - openai (GPT API)
  - ollama (local/remote Ollama)
- **TTS**: 
  - kokoro (neural TTS)
  - piper-tts (lightweight TTS)
- **Video Processing**: yt-dlp
- **Notifications**: requests (Telegram Bot API)
- **Audio**: soundfile, numpy, torch


## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

