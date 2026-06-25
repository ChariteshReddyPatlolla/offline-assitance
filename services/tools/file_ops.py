import os
from typing import Optional
from langchain_core.tools import tool
from services.tools.approval_store import require_approval
from services.tools.safety import should_require_path_approval
from shared.context import active_session_dir
from services.mcp.client import MCPClientManager

def _get_fallback_desktop() -> str:
    user_profile = os.environ.get("USERPROFILE", r"C:\Users\patlo")
    desktop = os.path.join(user_profile, "Desktop")
    onedrive_desktop = os.path.join(user_profile, "OneDrive", "Desktop")
    if os.path.exists(onedrive_desktop):
        return onedrive_desktop
    return desktop

@tool
def read_file(filepath: str) -> str:
    """
    Read the contents of a file.
    """
    current_dir = active_session_dir.get() or _get_fallback_desktop()
    if not os.path.isabs(filepath):
        filepath = os.path.join(current_dir, filepath)
    abs_path = os.path.abspath(filepath)
    
    return MCPClientManager.get_instance().call_tool(
        "filesystem", "read_file", filepath=abs_path
    )

@tool
def write_file(filepath: str, content: str, open_in_editor: Optional[str] = None) -> str:
    """
    Write content to a file.
    """
    current_dir = active_session_dir.get() or _get_fallback_desktop()
    if not os.path.isabs(filepath):
        filepath = os.path.join(current_dir, filepath)
    abs_path = os.path.abspath(filepath)

    return MCPClientManager.get_instance().call_tool(
        "filesystem", "write_file", filepath=abs_path, content=content, open_in_editor=open_in_editor
    )

@tool
def delete_file(filepath: str) -> str:
    """
    Delete a file.
    """
    current_dir = active_session_dir.get() or _get_fallback_desktop()
    if not os.path.isabs(filepath):
        filepath = os.path.join(current_dir, filepath)
    abs_path = os.path.abspath(filepath)

    protected = should_require_path_approval(abs_path)
    warning = "⚠️ This is a protected or high-risk file path.\n\n" if protected else ""

    approval = require_approval(
        action_key=f"delete:{abs_path}",
        description=(
            f"{warning}"
            f"Delete file:\n"
            f"```text\n{abs_path}\n```\n\n"
            f"⚠️ This action is irreversible."
        ),
        details={
            "filepath": abs_path,
            "protected": protected,
        },
        force=True,
    )

    if approval:
        return approval

    return MCPClientManager.get_instance().call_tool(
        "filesystem", "delete_file", filepath=abs_path
    )

@tool
def list_directory(dirpath: str = ".") -> str:
    """
    List the files and folders in a directory.
    """
    current_dir = active_session_dir.get() or _get_fallback_desktop()
    if not os.path.isabs(dirpath):
        dirpath = os.path.join(current_dir, dirpath)
    abs_path = os.path.abspath(dirpath)

    return MCPClientManager.get_instance().call_tool(
        "filesystem", "list_directory", dirpath=abs_path
    )

@tool
def create_directory(path: str) -> str:
    """
    Create a new directory at the specified path.
    """
    current_dir = active_session_dir.get() or _get_fallback_desktop()
    if not os.path.isabs(path):
        path = os.path.join(current_dir, path)
    abs_path = os.path.abspath(path)

    return MCPClientManager.get_instance().call_tool(
        "filesystem", "create_directory", path=abs_path
    )

@tool
def search_files(query: str, dirpath: str = ".", search_type: str = "filename") -> str:
    """
    Search recursively for files matching a pattern or files containing text.
    Args:
        query: Glob pattern (e.g. '*.py') or search string (e.g. 'import os')
        dirpath: Target folder path
        search_type: "filename" or "content"
    """
    current_dir = active_session_dir.get() or _get_fallback_desktop()
    if not os.path.isabs(dirpath):
        dirpath = os.path.join(current_dir, dirpath)
    abs_path = os.path.abspath(dirpath)
    return MCPClientManager.get_instance().call_tool(
        "filesystem", "search_files", query=query, dirpath=abs_path, search_type=search_type
    )

@tool
def move_file(src: str, dest: str, copy_only: bool = False) -> str:
    """
    Move or copy a file or directory from src to dest.
    """
    current_dir = active_session_dir.get() or _get_fallback_desktop()
    if not os.path.isabs(src):
        src = os.path.join(current_dir, src)
    if not os.path.isabs(dest):
        dest = os.path.join(current_dir, dest)
    abs_src = os.path.abspath(src)
    abs_dest = os.path.abspath(dest)
        
    return MCPClientManager.get_instance().call_tool(
        "filesystem", "move_file", src=abs_src, dest=abs_dest, copy_only=copy_only
    )