# OmniAgent v2.0 (Offline Assistance)

OmniAgent is an intelligent, agentic operating system interface designed to provide seamless, low-latency assistance. It bridges the gap between conversational AI and direct system-level automation, allowing users to interact with their computer naturally.

## 🚀 Features

- **Low-Latency Fast-Paths**: Instantly execute common commands without waiting for LLM generation. Supports locking the screen, controlling media, opening apps, typing text, web navigation, and more.
- **Autonomous Agentic OS**: Powered by LangGraph, the agent can autonomously break down complex tasks, write code, run scripts, and manage files.
- **Dual-Interface System**:
  - A modern Web UI (React/Vite) running on port `5173`.
  - A robust API Gateway (FastAPI) running on port `8000`.
- **Persistent Memory**: Uses SQLite (`omniagent.db`) for structured relational data and ChromaDB for semantic vector-based memory.
- **Desktop Context Awareness**: Tracks the active window, focused application, and open directories in real-time to provide context-aware responses.

## 📁 Project Structure

```text
├── agent_os/         # Core intelligent reasoning loops (LangGraph), executors, and agents
├── api/              # FastAPI Gateway for handling chat requests, tools, and endpoints
├── frontend/         # React/Vite web application for the chat dashboard
├── services/         # Background integrations, desktop automation (PyAutoGUI, OS hooks)
├── shared/           # Database schemas, models, and shared utilities
├── tests/            # Automated test suite (pytest)
├── workflows/        # Pre-defined automation workflows
└── main.py           # Entrypoint for headless autonomous loops
```

## 🛠️ Prerequisites

- **Python 3.10+**
- **Node.js 18+** (for the frontend)
- **Redis** (optional, for background task queuing)

## 🚦 Getting Started

### Quick Start (Windows)

The easiest way to launch the complete system is using the provided batch file:

```cmd
.\start.bat
```

This script will automatically:
1. Clean up stale ports.
2. Activate the Python virtual environment (`venv`).
3. Initialize the database schemas (`init_db.py`).
4. Start the FastAPI backend on `http://localhost:8000`.
5. Start the Vite React frontend on `http://localhost:5173`.

### Manual Setup

1. **Python Environment**:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Frontend Environment**:
   ```bash
   cd frontend
   npm install
   ```

3. **Running the API**:
   ```bash
   python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
   ```

4. **Running the Frontend**:
   ```bash
   cd frontend
   npm run dev
   ```

## 🖥️ Usage

Once running, navigate to `http://localhost:5173` to interact with the OmniAgent. You can:
- Type commands like *"Open visual studio code"* or *"Go to github.com"* for instant fast-path execution.
- Ask complex questions or request code generation where the agent will drop into a thinking state and spawn background workers to fulfill the task.
- Rely on contextual awareness; if you have a file open in Notepad or VSCode, you can refer to it as "this file".

---
*Developed as part of the Offline Assistance Project.*
