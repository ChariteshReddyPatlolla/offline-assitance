import os
import shutil
from typing import Optional


def read_file_raw(filepath: str) -> str:
    """Read the contents of a file."""
    try:
        if not os.path.exists(filepath):
            return f"❌ File not found: {filepath}"
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        max_chars = 6000
        if len(content) > max_chars:
            return (
                content[:max_chars]
                + "\n\n[... file truncated because it was too large ...]"
            )
        return content
    except Exception as e:
        return f"❌ Error reading file: {str(e)}"


def write_file_raw(filepath: str, content: str, open_in_editor: Optional[str] = None) -> str:
    """Write content to a file, optionally opening it in an editor.

    NOTE: 'filepath' should already be absolute from the wrapper. Do not re-resolve
    with os.path.abspath() to avoid subprocess cwd mismatch issues.
    """
    try:
        # Trust absolute paths as-is; only resolve relative paths
        abs_path = filepath if os.path.isabs(filepath) else os.path.abspath(filepath)
        parent = os.path.dirname(abs_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Update the active session file context so subsequent editor-open calls
        # can auto-attach this file without the LLM needing to repeat the path
        try:
            from shared.context import active_session_file
            active_session_file.set(abs_path)
        except Exception:
            pass

        # Automatically open in editor if requested
        editor_msg = ""
        if open_in_editor:
            editor_lower = open_in_editor.lower().strip()
            import subprocess

            # Use DETACHED_PROCESS so the editor is independent from the MCP server subprocess
            _flags = 0
            if hasattr(subprocess, "DETACHED_PROCESS"):
                _flags |= subprocess.DETACHED_PROCESS
            if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
                _flags |= subprocess.CREATE_NEW_PROCESS_GROUP

            if "vscode" in editor_lower or "code" in editor_lower:
                # Use the VS Code exe finder to avoid opening the web handler
                try:
                    from services.tools.impl.desktop import _find_vscode_exe
                    vscode_exe = _find_vscode_exe()
                except Exception:
                    vscode_exe = None

                try:
                    if vscode_exe:
                        subprocess.Popen(
                            [vscode_exe, abs_path],
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            close_fds=True,
                            creationflags=_flags,
                        )
                    else:
                        subprocess.Popen(
                            ["cmd", "/c", "start", "", "code", abs_path],
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            shell=False,
                            close_fds=True,
                            creationflags=_flags,
                        )
                    editor_msg = " and successfully opened in VS Code"
                except Exception as e_ed:
                    editor_msg = f" (failed to open in VS Code: {str(e_ed)})"

            elif "notepad" in editor_lower:
                try:
                    subprocess.Popen(
                        ["notepad.exe", abs_path],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        close_fds=True,
                        creationflags=_flags,
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


def delete_file_raw(filepath: str) -> str:
    """Delete a file."""
    try:
        abs_path = filepath if os.path.isabs(filepath) else os.path.abspath(filepath)
        if not os.path.exists(abs_path):
            return f"❌ File not found: {filepath}"
        if not os.path.isfile(abs_path):
            return f"❌ Not a file: {filepath}"
        os.remove(abs_path)
        return f"✅ Deleted:\n`{abs_path}`"
    except Exception as e:
        return f"❌ Error deleting file: {str(e)}"


def list_directory_raw(dirpath: str = ".") -> str:
    """List the contents of a directory."""
    try:
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


def create_directory_raw(path: str) -> str:
    """Create a new directory at the specified path.

    NOTE: 'path' must already be an absolute path. Do NOT call os.path.abspath()
    here because this function may run inside an MCP server subprocess whose cwd
    differs from the user's Desktop. The wrapper in services/tools/file_ops.py
    already resolves the absolute path before passing it here.
    """
    try:
        # Ensure the path is treated as-is if absolute; only normalize if relative
        if not os.path.isabs(path):
            user_profile = os.environ.get("USERPROFILE", r"C:\Users\patlo")
            desktop = os.path.join(user_profile, "Desktop")
            onedrive_desktop = os.path.join(user_profile, "OneDrive", "Desktop")
            if os.path.exists(onedrive_desktop):
                desktop = onedrive_desktop
            path = os.path.join(desktop, path)
        os.makedirs(path, exist_ok=True)
        return f"✅ Directory created successfully: `{path}`"
    except Exception as e:
        return f"❌ Error creating directory: {str(e)}"

def search_files_raw(query: str, dirpath: str = ".", search_type: str = "filename") -> str:
    """Search recursively for files matching a pattern or files containing text."""
    try:
        import fnmatch
        if not os.path.exists(dirpath):
            return f"❌ Target directory not found: {dirpath}"
            
        results = []
        search_type_lower = search_type.lower().strip()
        
        for root, dirs, files in os.walk(dirpath):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', '__pycache__', 'venv', '.git')]
            for file in files:
                full_path = os.path.join(root, file)
                if search_type_lower == "filename":
                    if fnmatch.fnmatch(file.lower(), query.lower()):
                        results.append(full_path)
                elif search_type_lower == "content":
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        if query.lower() in content.lower():
                            results.append(full_path)
                    except Exception:
                        pass
                        
        if not results:
            return f"No matching files found for query '{query}' (type: {search_type_lower}) under '{dirpath}'."
            
        output = [f"Found {len(results)} matches (showing up to 50):"]
        for r in results[:50]:
            output.append(f"- `{r}`")
        if len(results) > 50:
            output.append(f"... and {len(results) - 50} more files.")
        return "\n".join(output)
    except Exception as e:
        return f"❌ Error searching files: {str(e)}"

def move_file_raw(src: str, dest: str, copy_only: bool = False) -> str:
    """Move or copy a file or directory from src to dest."""
    try:
        if not os.path.exists(src):
            return f"❌ Source path does not exist: {src}"
            
        dest_parent = os.path.dirname(dest)
        if dest_parent:
            os.makedirs(dest_parent, exist_ok=True)
            
        if copy_only:
            if os.path.isdir(src):
                shutil.copytree(src, dest, dirs_exist_ok=True)
                return f"✅ Copied directory from `{src}` to `{dest}`."
            else:
                shutil.copy2(src, dest)
                return f"✅ Copied file from `{src}` to `{dest}`."
        else:
            shutil.move(src, dest)
            return f"✅ Moved `{src}` to `{dest}`."
    except Exception as e:
        return f"❌ Error moving/copying file: {str(e)}"
