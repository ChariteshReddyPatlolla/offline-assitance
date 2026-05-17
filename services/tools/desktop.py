import os
import subprocess
import webbrowser
from langchain_core.tools import tool


@tool
def open_application(app_name: str) -> str:
    """
    Open a desktop application or program by name.
    Examples: 'notepad', 'calculator', 'chrome', 'vscode', 'explorer', 'cmd'
    Also handles special names like 'file explorer', 'vs code', 'visual studio code'.
    """
    name_lower = app_name.lower().strip()

    # Common name mappings
    aliases = {
        "file explorer": "explorer",
        "files": "explorer",
        "vs code": "code",
        "visual studio code": "code",
        "vscode": "code",
        "terminal": "cmd",
        "command prompt": "cmd",
        "powershell": "powershell",
        "notepad": "notepad",
        "calculator": "calc",
        "chrome": "chrome",
        "google chrome": "chrome",
        "firefox": "firefox",
        "edge": "msedge",
        "microsoft edge": "msedge",
        "task manager": "taskmgr",
        "paint": "mspaint",
        "word": "winword",
        "excel": "excel",
        "spotify": "spotify",
    }

    executable = aliases.get(name_lower, name_lower)

    try:
        # Try using the Windows 'start' command (handles paths, app names, .exe)
        subprocess.Popen(
            ["cmd", "/c", "start", "", executable],
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        return f"✅ Opened '{app_name}' successfully."
    except Exception as e1:
        try:
            os.startfile(executable)
            return f"✅ Opened '{app_name}' successfully."
        except Exception as e2:
            return f"❌ Could not open '{app_name}'. Error: {str(e2)}"


@tool
def take_screenshot_description() -> str:
    """
    Describes the current screen state. Returns a summary of what's visible.
    Used to understand the desktop context before taking actions.
    """
    try:
        import pyautogui
        size = pyautogui.size()
        pos = pyautogui.position()
        return f"Screen size: {size.width}x{size.height}. Current mouse position: ({pos.x}, {pos.y})."
    except ImportError:
        return "Screen info: pyautogui not available. Operating on Windows desktop."
    except Exception as e:
        return f"Screen info unavailable: {str(e)}"


@tool
def type_text_at_cursor(text: str) -> str:
    """
    Types the given text at the current cursor position using keyboard simulation.
    Use this to fill in forms, write code, or input text into any application.
    """
    try:
        import pyautogui
        import time
        time.sleep(0.5)  # Small delay to let user focus the target window
        pyautogui.typewrite(text, interval=0.03)
        return f"✅ Typed: '{text[:50]}{'...' if len(text) > 50 else ''}'"
    except ImportError:
        return "❌ pyautogui not available. Cannot type text."
    except Exception as e:
        return f"❌ Error typing text: {str(e)}"


@tool
def press_hotkey(keys: str) -> str:
    """
    Press a keyboard shortcut or hotkey combination.
    Examples: 'ctrl+c', 'ctrl+v', 'alt+tab', 'win+d', 'ctrl+shift+esc'
    """
    try:
        import pyautogui
        key_list = [k.strip() for k in keys.lower().split("+")]
        pyautogui.hotkey(*key_list)
        return f"✅ Pressed hotkey: {keys}"
    except ImportError:
        return "❌ pyautogui not available."
    except Exception as e:
        return f"❌ Error pressing hotkey '{keys}': {str(e)}"
