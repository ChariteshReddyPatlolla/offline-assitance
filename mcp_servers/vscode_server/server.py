import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from mcp.server.fastmcp import FastMCP
from services.tools.impl.desktop import (
    run_editor_sync_demo_raw,
    open_file_in_vscode_raw,
    open_folder_in_vscode_raw,
    run_command_in_vscode_terminal_raw
)

mcp = FastMCP("vscode")

@mcp.tool()
def run_editor_sync_demo() -> str:
    """
    Natively automates the complete visual VS Code and Notepad editor synchronization demo.
    """
    return run_editor_sync_demo_raw()

@mcp.tool()
def open_file_in_vscode(filepath: str) -> str:
    """Open a file in the VS Code desktop app."""
    return open_file_in_vscode_raw(filepath)

@mcp.tool()
def open_folder_in_vscode(folderpath: str) -> str:
    """Open a folder in the VS Code desktop app."""
    return open_folder_in_vscode_raw(folderpath)

@mcp.tool()
def run_command_in_vscode_terminal(command: str) -> str:
    """Focus VS Code, open the integrated terminal, and execute a command."""
    return run_command_in_vscode_terminal_raw(command)

if __name__ == "__main__":
    mcp.run()
