# Time Reclamation App

Reclaim time wasted on social media by getting curated summaries instead of endless scrolling.

## 🎯 Problem Statement
Helps users reduce time on social platforms without complete abandonment, addressing FOMO and dopamine dependency through intelligent content curation.

## 📁 Project Structure

```
TimeReclamation/
├── main.py                          # Main entry point
├── requirements.txt                 # Python dependencies
├── src/time_reclamation/           # Main package
│   ├── config/                     # Configuration management
│   ├── core/                       # Core business logic
│   │   ├── extractors/            # Content extraction modules
│   │   ├── processors/            # LLM processing and summarization
│   │   └── schedulers/            # Task scheduling algorithms
│   ├── infrastructure/            # Infrastructure services
│   │   ├── cache/                 # Caching system
│   │   ├── llm/                   # Local LLM integration
│   │   └── notifications/         # Notification providers
│   └── interfaces/                # User interfaces
│       ├── cli/                   # Command-line interface
│       └── api/                   # REST API endpoints
└── tests/                         # Test suites
```

## 🚀 Features

### Supported Platforms
- **YouTube**: Channel summaries with key timestamps
- **Reddit**: Subreddit content filtering and summarization
- **X (Twitter)**: Following feed insights

### Core Capabilities
- Local LLM processing for privacy
- Customizable summary length
- Multi-platform notifications (Telegram, WhatsApp)
- Flexible content filtering
- Quiet hours configuration

## 🔧 Setup

1. Clone repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure platforms and notification preferences
4. Run: `python main.py`

## 📱 Notifications

Supported delivery methods:
- Telegram bot
- Email (planned)
- Discord (planned)