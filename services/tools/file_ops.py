import os
from langchain_core.tools import tool
from services.tools.approval_store import require_approval
from services.tools.safety import is_protected_path, is_dangerous_command, get_safety_warning


@tool
def read_file(filepath: str) -> str:
    """
    Read the contents of a file at the given filepath.
    Use this to view code, config files, text documents, or logs.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) > 6000:
            return content[:6000] + "\n\n[... file truncated ...]"
        return content
    except FileNotFoundError:
        return f"❌ File not found: {filepath}"
    except Exception as e:
        return f"❌ Error reading file: {str(e)}"


@tool
def write_file(filepath: str, content: str) -> str:
    """
    Write content to a file. REQUIRES USER APPROVAL.
    Use this to save code, create documents, or modify configuration files.
    """
    abs_path = os.path.abspath(filepath)

    # Safety check — protected system paths always require approval and cannot be bypassed
    force = is_protected_path(abs_path)
    warning = "⚠️ This is a PROTECTED SYSTEM PATH. Extra caution required. " if force else ""

    action_key = f"write:{abs_path}"
    approval = require_approval(
        action_key=action_key,
        description=f"{warning}Write to file: `{filepath}` ({len(content)} characters)",
        details={"filepath": abs_path, "content_preview": content[:300], "protected": force},
        force=force,
    )
    if approval:
        return approval

    try:
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✅ Successfully wrote {len(content)} characters to '{filepath}'"
    except Exception as e:
        return f"❌ Error writing file: {str(e)}"


@tool
def delete_file(filepath: str) -> str:
    """
    Delete a file. ALWAYS REQUIRES USER APPROVAL — this action is irreversible.
    Use this only when explicitly asked to delete a file.
    """
    abs_path = os.path.abspath(filepath)
    force = is_protected_path(abs_path)
    warning = "⚠️ PROTECTED SYSTEM PATH — " if force else ""

    action_key = f"delete:{abs_path}"
    approval = require_approval(
        action_key=action_key,
        description=f"{warning}Delete file: `{filepath}` — **This is irreversible!**",
        details={"filepath": abs_path, "protected": force},
        force=True,  # Always force approval for deletions
    )
    if approval:
        return approval

    try:
        if not os.path.exists(abs_path):
            return f"❌ File not found: {filepath}"
        os.remove(abs_path)
        return f"✅ Deleted '{filepath}'"
    except Exception as e:
        return f"❌ Error deleting file: {str(e)}"


@tool
def list_directory(dirpath: str = ".") -> str:
    """
    List the files and folders in a directory.
    """
    try:
        items = os.listdir(dirpath)
        dirs = [f"📁 {i}/" for i in sorted(items) if os.path.isdir(os.path.join(dirpath, i))]
        files = [f"📄 {i}" for i in sorted(items) if os.path.isfile(os.path.join(dirpath, i))]
        return f"Contents of '{dirpath}':\n" + "\n".join(dirs + files)
    except Exception as e:
        return f"❌ Error listing directory: {str(e)}"
