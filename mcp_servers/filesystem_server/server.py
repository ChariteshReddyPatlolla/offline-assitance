import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from mcp.server.fastmcp import FastMCP
from services.tools.impl.file_ops import (
    read_file_raw,
    write_file_raw,
    delete_file_raw,
    list_directory_raw,
    create_directory_raw,
    search_files_raw,
    move_file_raw
)

from typing import Optional

mcp = FastMCP("filesystem")

@mcp.tool()
def read_file(filepath: str) -> str:
    """Read the contents of a file."""
    return read_file_raw(filepath)

@mcp.tool()
def write_file(filepath: str, content: str, open_in_editor: Optional[str] = None) -> str:
    """Write content to a file."""
    return write_file_raw(filepath, content, open_in_editor)

@mcp.tool()
def delete_file(filepath: str) -> str:
    """Delete a file."""
    return delete_file_raw(filepath)

@mcp.tool()
def list_directory(dirpath: str = ".") -> str:
    """List the contents of a directory."""
    return list_directory_raw(dirpath)

@mcp.tool()
def create_directory(path: str) -> str:
    """Create a new directory at the specified path."""
    return create_directory_raw(path)

@mcp.tool()
def search_files(query: str, dirpath: str = ".", search_type: str = "filename") -> str:
    """Search recursively for files matching a pattern or files containing text.
    Args:
        query: Glob pattern (e.g. '*.py') or search string (e.g. 'import os')
        dirpath: Target folder path
        search_type: "filename" or "content"
    """
    return search_files_raw(query, dirpath, search_type)

@mcp.tool()
def move_file(src: str, dest: str, copy_only: bool = False) -> str:
    """Move or copy a file or directory from src to dest."""
    return move_file_raw(src, dest, copy_only)

if __name__ == "__main__":
    mcp.run()
