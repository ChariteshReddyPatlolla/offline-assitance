# OmniAgent - Offline First AI Assistant

OmniAgent is a highly responsive, privacy-focused, offline-first AI desktop assistant. It seamlessly integrates a blazingly fast local command routing engine ("Fast-path") with a powerful, background-queued LLM (running via Ollama) to tackle complex tasks without ever locking up your UI.

## Features

- **Zero-Latency Fast-Path**: Simple requests like "open whatsapp", "volume up", or "type this" are intercepted instantly via Regex, bypassing the LLM entirely for instantaneous execution.
- **Synchronous LLM Code Editor**: Code update requests ("add a line", "update the code", "delete the part") are processed directly by the local LLM and applied to your active script in real-time, bypassing the background queue for instant development iteration.
- **Lenient Command Routing**: The fast-path regex engine is highly robust, smoothly catching natural language variations (like "also add...", "pause the video", "play it") without requiring strict keyword memorization.
- **Background LLM Worker**: Complex requests are securely routed through a Redis queue to a background agent that writes its "thoughts" dynamically into a local markdown file before delivering the final result.
- **Continuous Voice Copilot**: Speak naturally. The microphone automatically calibrates to your environment, transcribes your voice to text using `SpeechRecognition`, and replies audibly using local Text-to-Speech (`pyttsx3`) before seamlessly continuing to listen.
- **Total Privacy**: All processing (both Fast-path actions and LLM inference) occurs locally on your machine. No data leaves your device.
- **Context-Aware**: Built-in trackers monitor your active window and working directory, giving OmniAgent full awareness of what you are currently looking at on your screen.

## Installation

1. Ensure Python 3.10+ is installed.
2. Install Ollama and ensure the `llama3.1:8b` model is downloaded locally.
3. Install Redis and start the Redis server (or use the provided `Redis` folder binaries).
4. Run `pip install -r requirements.txt`.

## Usage

Simply run the master startup script:

```bash
start.bat
```

This will automatically:
1. Initialize the SQLite context database.
2. Boot up the FastAPI backend (`api.main:app`).
3. Start the Vite React frontend.

You can then access the interface at `http://localhost:5173`.

### Floating Edge UI
For a truly integrated desktop experience, you can also launch the application in a compact, floating window format:
```bash
start-floating-chat.bat
```

## Architecture

- **Backend**: FastAPI (Python) routing requests between `chat.py`, `voice.py`, and the background worker (`services/fast_path.py`).
- **Frontend**: React + Vite + Tauri, featuring dual-mode interfaces (Full Page vs. Floating Compact).
- **Agent Framework**: LangGraph.
- **Queueing**: Redis + generic worker pattern.
