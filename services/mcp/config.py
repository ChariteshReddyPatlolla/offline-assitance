import os
import sys

# From services/mcp/config.py, root is two levels up
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Normalize path for subprocess compatibility
PROJECT_ROOT_NORM = PROJECT_ROOT.replace("\\", "/")

# Python interpreter path from the active virtual environment
PYTHON_EXE = sys.executable.replace("\\", "/")

MCP_SERVERS = {
    "filesystem": {
        "transport": "stdio",
        "command": PYTHON_EXE,
        "args": [f"{PROJECT_ROOT_NORM}/mcp_servers/filesystem_server/server.py"]
    },
    "shell": {
        "transport": "stdio",
        "command": PYTHON_EXE,
        "args": [f"{PROJECT_ROOT_NORM}/mcp_servers/shell_server/server.py"]
    },
    "browser": {
        "transport": "stdio",
        "command": PYTHON_EXE,
        "args": [f"{PROJECT_ROOT_NORM}/mcp_servers/browser_server/server.py"]
    },
    "git": {
        "transport": "stdio",
        "command": PYTHON_EXE,
        "args": [f"{PROJECT_ROOT_NORM}/mcp_servers/git_server/server.py"]
    },
    "email": {
        "transport": "stdio",
        "command": PYTHON_EXE,
        "args": [f"{PROJECT_ROOT_NORM}/mcp_servers/email_server/server.py"]
    },
    "pdf": {
        "transport": "stdio",
        "command": PYTHON_EXE,
        "args": [f"{PROJECT_ROOT_NORM}/mcp_servers/pdf_server/server.py"]
    },
    "research": {
        "transport": "stdio",
        "command": PYTHON_EXE,
        "args": [f"{PROJECT_ROOT_NORM}/mcp_servers/research_server/server.py"]
    },
    "automation": {
        "transport": "stdio",
        "command": PYTHON_EXE,
        "args": [f"{PROJECT_ROOT_NORM}/mcp_servers/automation_server/server.py"]
    },
    "vscode": {
        "transport": "stdio",
        "command": PYTHON_EXE,
        "args": [f"{PROJECT_ROOT_NORM}/mcp_servers/vscode_server/server.py"]
    },
    "sqlite": {
        "transport": "stdio",
        "command": PYTHON_EXE,
        "args": [f"{PROJECT_ROOT_NORM}/mcp_servers/sqlite_server/server.py"]
    }
}
