"""
File operations tools for OmniAgent.

Security Policy
---------------
- Reading files does NOT require approval.
- Listing directories does NOT require approval.
- Writing to protected paths requires approval.
- Deleting files ALWAYS requires approval.
- Approval prompts are shown directly in the chat with the exact file path.
"""

import os
from langchain_core.tools import tool

from services.tools.approval_store import require_approval
from services.tools.safety import should_require_path_approval
from shared.context import active_session_dir


def _get_fallback_desktop() -> str:
    user_profile = os.environ.get("USERPROFILE", r"C:\Users\patlo")
    desktop = os.path.join(user_profile, "Desktop")
    onedrive_desktop = os.path.join(user_profile, "OneDrive", "Desktop")
    if os.path.exists(onedrive_desktop):
        return onedrive_desktop
    return desktop



# ============================================================================
# READ FILE
# ============================================================================

@tool
def read_file(filepath: str) -> str:
    """
    Read the contents of a file.

    Use this to:
    - View code
    - Inspect configuration files
    - Read text documents
    - Check logs
    """
    try:
        current_dir = active_session_dir.get() or _get_fallback_desktop()
        if not os.path.isabs(filepath):
            filepath = os.path.join(current_dir, filepath)

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        max_chars = 6000
        if len(content) > max_chars:
            return (
                content[:max_chars]
                + "\n\n[... file truncated because it was too large ...]"
            )

        return content

    except FileNotFoundError:
        return f"❌ File not found: {filepath}"

    except Exception as e:
        return f"❌ Error reading file: {str(e)}"


# ============================================================================
# WRITE FILE
# ============================================================================

@tool
def write_file(filepath: str, content: str, open_in_editor: str = None) -> str:
    """
    Write content to a file.

    Parameters:
    - filepath: The path to write the file.
    - content: The content to write.
    - open_in_editor: Optional. Open the file in an active editor after writing. Supported values: 'vscode' (opens in VS Code), 'notepad' (opens in Notepad).

    Security:
    - Writing to protected paths requires approval.
    - Approval prompt includes file path and content preview.
    """
    current_dir = active_session_dir.get() or _get_fallback_desktop()
    if not os.path.isabs(filepath):
        filepath = os.path.join(current_dir, filepath)

    abs_path = os.path.abspath(filepath)

    # Determine whether this path requires approval
    protected = should_require_path_approval(abs_path)

    warning = (
        "⚠️ This is a protected or high-risk file path.\n\n"
        if protected
        else ""
    )

    approval = require_approval(
        action_key=f"write:{abs_path}",
        description=(
            f"{warning}"
            f"Write to file:\n"
            f"```text\n{abs_path}\n```\n\n"
            f"Content length: {len(content)} characters"
        ),
        details={
            "filepath": abs_path,
            "content_preview": content[:500],
            "protected": protected,
        },
        force=protected,
    )

    if approval:
        return approval

    try:
        parent = os.path.dirname(abs_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Automatically open in editor if requested
        editor_msg = ""
        if open_in_editor:
            editor_lower = open_in_editor.lower().strip()
            import subprocess
            if "vscode" in editor_lower or "code" in editor_lower:
                try:
                    subprocess.Popen(
                        ["cmd", "/c", "start", "", "code", abs_path],
                        shell=False,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                    )
                    editor_msg = " and successfully opened in VS Code"
                except Exception as e_ed:
                    editor_msg = f" (failed to open in VS Code: {str(e_ed)})"
            elif "notepad" in editor_lower:
                try:
                    subprocess.Popen(
                        ["cmd", "/c", "start", "", "notepad", abs_path],
                        shell=False,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                    )
                    editor_msg = " and successfully opened in Notepad"
                except Exception as e_ed:
                    editor_msg = f" (failed to open in Notepad: {str(e_ed)})"

        return (
            f"✅ Successfully wrote {len(content)} characters to:\n"
            f"`{abs_path}`{editor_msg}"
        )

    except Exception as e:
        return f"❌ Error writing file: {str(e)}"


# ============================================================================
# DELETE FILE
# ============================================================================

@tool
def delete_file(filepath: str) -> str:
    """
    Delete a file.

    Security:
    - ALWAYS requires approval.
    - Action is irreversible.
    """
    current_dir = active_session_dir.get() or _get_fallback_desktop()
    if not os.path.isabs(filepath):
        filepath = os.path.join(current_dir, filepath)

    abs_path = os.path.abspath(filepath)

    protected = should_require_path_approval(abs_path)

    warning = (
        "⚠️ This is a protected or high-risk file path.\n\n"
        if protected
        else ""
    )

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
        force=True,  # Always require approval for deletions
    )

    if approval:
        return approval

    try:
        if not os.path.exists(abs_path):
            return f"❌ File not found: {filepath}"

        if not os.path.isfile(abs_path):
            return f"❌ Not a file: {filepath}"

        os.remove(abs_path)

        return f"✅ Deleted:\n`{abs_path}`"

    except Exception as e:
        return f"❌ Error deleting file: {str(e)}"


# ============================================================================
# LIST DIRECTORY
# ============================================================================

@tool
def list_directory(dirpath: str = ".") -> str:
    """
    List the files and folders in a directory.
    """
    try:
        current_dir = active_session_dir.get() or _get_fallback_desktop()
        if not os.path.isabs(dirpath):
            dirpath = os.path.join(current_dir, dirpath)

        items = os.listdir(dirpath)

        directories = [
            f"📁 {name}/"
            for name in sorted(items)
            if os.path.isdir(os.path.join(dirpath, name))
        ]

        files = [
            f"📄 {name}"
            for name in sorted(items)
            if os.path.isfile(os.path.join(dirpath, name))
        ]

        output = directories + files

        if not output:
            return f"Directory is empty: `{dirpath}`"

        return f"Contents of `{dirpath}`:\n\n" + "\n".join(output)

    except FileNotFoundError:
        return f"❌ Directory not found: {dirpath}"

    except PermissionError:
        return f"❌ Permission denied: {dirpath}"

    except Exception as e:
        return f"❌ Error listing directory: {str(e)}"