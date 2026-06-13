import os
import subprocess
import time
import shutil
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _find_vscode_exe() -> Optional[str]:
    """Find the VS Code desktop executable (Code.exe) on Windows.
    
    Searches known installation paths. The per-user AppData path is the most
    common install location on Windows 10/11 when VS Code is installed without admin rights.
    """
    user = os.environ.get("USERPROFILE", r"C:\Users\patlo")
    local_app = os.environ.get("LOCALAPPDATA", os.path.join(user, "AppData", "Local"))

    candidates = [
        # ✅ Confirmed install path for this machine
        r"C:\Users\patlo\AppData\Local\Programs\Microsoft VS Code\Code.exe",
        # Per-user install via LOCALAPPDATA env var (most portable)
        os.path.join(local_app, r"Programs\Microsoft VS Code\Code.exe"),
        # Per-user install via USERPROFILE
        os.path.join(user, r"AppData\Local\Programs\Microsoft VS Code\Code.exe"),
        # System-wide installs
        r"C:\Program Files\Microsoft VS Code\Code.exe",
        r"C:\Program Files (x86)\Microsoft VS Code\Code.exe",
        # Insiders builds
        os.path.join(local_app, r"Programs\Microsoft VS Code Insiders\Code - Insiders.exe"),
        os.path.join(user, r"AppData\Local\Programs\Microsoft VS Code Insiders\Code - Insiders.exe"),
        r"C:\Program Files\Microsoft VS Code Insiders\Code - Insiders.exe",
    ]
    for p in candidates:
        if os.path.isfile(p):
            logger.info("Found VS Code exe at: %s", p)
            return p

    # Ultimate fallback: search PATH for code.exe (not code.cmd which triggers URI handler)
    try:
        import shutil as _shutil
        which = _shutil.which("Code.exe") or _shutil.which("code.exe")
        if which and os.path.isfile(which) and which.lower().endswith(".exe"):
            logger.info("Found VS Code exe via PATH: %s", which)
            return which
    except Exception:
        pass

    logger.warning("VS Code exe not found in any known location")
    return None




def _make_detached_popen(cmd_args, shell=False):
    """Launch a process fully detached from the MCP server subprocess.
    
    Using DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP ensures the child
    process keeps running even after the MCP server subprocess exits.
    """
    flags = 0
    if hasattr(subprocess, "DETACHED_PROCESS"):
        flags |= subprocess.DETACHED_PROCESS
    if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        flags |= subprocess.CREATE_NEW_PROCESS_GROUP
    return subprocess.Popen(
        cmd_args,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=shell,
        close_fds=True,
        creationflags=flags,
    )


def open_application_raw(app_name: str, path: Optional[str] = None) -> str:
    """Open a desktop application or program by name.
    
    For VS Code: always finds and launches the local .exe directly so it opens
    as a desktop app, NOT as the vscode:// web URI.
    For Notepad/editors: if path is None, tries to use the active session file.
    """
    name_lower = app_name.lower().strip()

    aliases = {
        "file explorer": "explorer",
        "files": "explorer",
        "vs code": "vscode",
        "visual studio code": "vscode",
        "vscode": "vscode",
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

    # ---- Special case: VS Code — launch the .exe directly, never via 'code' shorthand ----
    if executable == "vscode":
        vscode_exe = _find_vscode_exe()
        if vscode_exe:
            try:
                cmd = [vscode_exe]
                if path:
                    cmd.append(path)
                _make_detached_popen(cmd)
                return f"✅ Opened VS Code (desktop app) successfully{' with ' + path if path else ''}."
            except Exception as e:
                logger.warning("Failed to launch VS Code via exe: %s", e)
        # Fallback: use powershell Start-Process which doesn't trigger web handler
        try:
            ps_cmd = f'Start-Process "code" {("-ArgumentList \'" + path + "\'") if path else ""}'
            _make_detached_popen(["powershell", "-WindowStyle", "Hidden", "-Command", ps_cmd])
            return f"✅ Opened VS Code successfully{' with ' + path if path else ''}."
        except Exception as e:
            return f"❌ Could not open VS Code: {str(e)}"

    # ---- Special case: Notepad — attach current session file if path is not given ----
    if executable == "notepad":
        target_path = path
        if not target_path:
            # Try to get the active session file from context
            try:
                from shared.context import active_session_file
                target_path = active_session_file.get()
            except Exception:
                pass
        try:
            cmd = ["notepad.exe"]
            if target_path and os.path.isfile(target_path):
                cmd.append(target_path)
            _make_detached_popen(cmd)
            if target_path and os.path.isfile(target_path):
                return f"✅ Opened '{os.path.basename(target_path)}' in Notepad."
            return "✅ Opened Notepad."
        except Exception as e:
            return f"❌ Could not open Notepad: {str(e)}"

    # ---- General case: all other apps ----
    try:
        cmd_args = ["cmd", "/c", "start", "", executable]
        if path:
            cmd_args.append(path)
        _make_detached_popen(cmd_args)
        return f"✅ Opened '{app_name}' successfully."
    except Exception as e1:
        try:
            if path:
                os.startfile(path)
            else:
                os.startfile(executable)
            return f"✅ Opened '{app_name}' successfully."
        except Exception as e2:
            return f"❌ Could not open '{app_name}'. Error: {str(e2)}"

def take_screenshot_description_raw() -> str:
    """Describes the current screen size and cursor state."""
    try:
        import pyautogui
        size = pyautogui.size()
        pos = pyautogui.position()
        return f"Screen size: {size.width}x{size.height}. Current mouse position: ({pos.x}, {pos.y})."
    except ImportError:
        return "Screen info: pyautogui not available. Operating on Windows desktop."
    except Exception as e:
        return f"Screen info unavailable: {str(e)}"

def type_text_at_cursor_raw(text: str) -> str:
    """Types the given text at the current cursor position."""
    try:
        import pyautogui
        time.sleep(0.5)
        pyautogui.typewrite(text, interval=0.03)
        return f"✅ Typed: '{text[:50]}{'...' if len(text) > 50 else ''}'"
    except ImportError:
        return "❌ pyautogui not available. Cannot type text."
    except Exception as e:
        return f"❌ Error typing text: {str(e)}"

def press_hotkey_raw(keys: str) -> str:
    """Press a keyboard shortcut shortcut or hotkey combination."""
    try:
        import pyautogui
        key_list = [k.strip() for k in keys.lower().split("+")]
        pyautogui.hotkey(*key_list)
        return f"✅ Pressed hotkey: {keys}"
    except ImportError:
        return "❌ pyautogui not available."
    except Exception as e:
        return f"❌ Error pressing hotkey '{keys}': {str(e)}"

def close_application_raw(app_name: str) -> str:
    """Closes a desktop application or specific window by its name or title."""
    name_lower = app_name.lower().strip()
    
    if "youtube" in name_lower or "yt" in name_lower:
        try:
            from services.tools.impl.browser import close_persistent_browser
            if close_persistent_browser():
                return "✅ Closed the automated YouTube persistent browser window."
            else:
                return "ℹ️ No automated YouTube session was active."
        except Exception as e:
            return f"❌ Error trying to close YouTube: {str(e)}"
            
    aliases = {
        "chrome": "chrome",
        "google chrome": "chrome",
        "brave": "brave",
        "brave browser": "brave",
        "firefox": "firefox",
        "edge": "msedge",
        "microsoft edge": "msedge",
        "notepad": "notepad",
        "calculator": "calc",
        "vs code": "code",
        "visual studio code": "code",
        "vscode": "code",
        "explorer": "explorer",
        "file explorer": "explorer",
        "spotify": "spotify",
    }
    
    executable = aliases.get(name_lower, name_lower)
    
    cmd_graceful = f'powershell -Command "Get-Process -Name \'{executable}\' -ErrorAction SilentlyContinue | ForEach-Object {{ $_.CloseMainWindow() }}"'
    try:
        subprocess.run(cmd_graceful, stdin=subprocess.DEVNULL, shell=True, capture_output=True, text=True)
        cmd_check = f'powershell -Command "Get-Process -Name \'{executable}\' -ErrorAction SilentlyContinue"'
        check_res = subprocess.run(cmd_check, stdin=subprocess.DEVNULL, shell=True, capture_output=True, text=True)
        if not check_res.stdout.strip():
            return f"✅ Closed '{app_name}' gracefully."
    except Exception:
        pass
        
    try:
        subprocess.run(f"taskkill /IM {executable}.exe /F", stdin=subprocess.DEVNULL, shell=True, capture_output=True, text=True)
        subprocess.run(f"taskkill /IM {executable} /F", stdin=subprocess.DEVNULL, shell=True, capture_output=True, text=True)
        return f"✅ Closed '{app_name}' successfully."
    except Exception as e:
        return f"❌ Could not close '{app_name}'. Error: {str(e)}"

def run_editor_sync_demo_raw() -> str:
    """Natively automates the complete visual VS Code and Notepad editor synchronization demo."""
    user_profile = os.environ.get("USERPROFILE", r"C:\Users\patlo")
    desktop = os.path.join(user_profile, "Desktop")
    if not os.path.exists(desktop):
        desktop = os.path.join(user_profile, "OneDrive", "Desktop")
        
    demo_dir = os.path.join(desktop, "agent_demo")
    file_path = os.path.join(demo_dir, "main.py")

    try:
        import pyautogui
    except ImportError:
        return "❌ PyAutoGUI is not installed in the active environment. Cannot run visual desktop automation."

    pyautogui.FAILSAFE = False

    def focus_window(title_substring: str):
        cmd = f"powershell -Command \"$ws = New-Object -ComObject wscript.shell; [void]$ws.AppActivate('{title_substring}')\""
        subprocess.run(cmd, stdin=subprocess.DEVNULL, shell=True, capture_output=True)
        time.sleep(1.5)

    logger.info("Step 1: Creating agent_demo folder on Desktop...")
    os.makedirs(demo_dir, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("")
    time.sleep(2)

    logger.info("Step 2: Launching VS Code...")
    subprocess.Popen(["cmd", "/c", "start", "", "code", demo_dir, file_path], stdin=subprocess.DEVNULL, shell=False)
    time.sleep(12)

    logger.info("Step 3: Typing print inside VS Code...")
    focus_window("Visual Studio Code")
    focus_window("main.py")
    
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.5)
    pyautogui.press("backspace")
    time.sleep(0.5)
    
    pyautogui.typewrite('print("Hello from VS Code")\n', interval=0.03)
    time.sleep(1)
    
    pyautogui.hotkey("ctrl", "s")
    time.sleep(2)

    logger.info("Step 4: Opening in Notepad...")
    subprocess.Popen(["cmd", "/c", "start", "", "notepad", file_path], stdin=subprocess.DEVNULL, shell=False)
    time.sleep(4)

    logger.info("Step 5: Typing inside Notepad...")
    focus_window("Notepad")
    focus_window("main.py - Notepad")
    
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.5)
    pyautogui.press("backspace")
    time.sleep(0.5)
    
    pyautogui.typewrite('print("Hello from Notepad")\nprint("This file was edited by the OmniAgent")\n', interval=0.03)
    time.sleep(1.5)
    
    pyautogui.hotkey("ctrl", "s")
    time.sleep(1.5)
    pyautogui.hotkey("alt", "f4")
    time.sleep(2.5)

    logger.info("Step 6 & 7: Return to VS Code and toggle integrated terminal...")
    focus_window("Visual Studio Code")
    focus_window("main.py")
    time.sleep(1.5)
    
    pyautogui.hotkey("ctrl", "`")
    time.sleep(3.5)

    logger.info("Step 8: Execute in VS Code terminal...")
    pyautogui.typewrite("python main.py\n", interval=0.03)
    time.sleep(10)

    logger.info("Step 9: Close editor...")
    pyautogui.hotkey("ctrl", "`")
    time.sleep(1.5)
    pyautogui.hotkey("ctrl", "w")
    time.sleep(1.5)
    
    focus_window("Visual Studio Code")
    pyautogui.hotkey("alt", "f4")
    time.sleep(4.5)

    logger.info("Step 10: Delete Desktop folder...")
    time.sleep(3)
    try:
        shutil.rmtree(demo_dir)
        logger.info("Desktop folder deleted successfully!")
    except Exception as e_del:
        logger.warning("Folder deletion warning: %s", str(e_del))

    return (
        "✅ Visual VS Code and Notepad synchronization workflow demo executed successfully!\n"
        "Created workspace, synchronized edits in real-time, executed in terminal, and cleaned up."
    )

def open_file_in_vscode_raw(filepath: str) -> str:
    """Open a file in the VS Code desktop app."""
    abs_path = filepath if os.path.isabs(filepath) else os.path.abspath(filepath)
    if not os.path.exists(abs_path):
        try:
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write("")
        except Exception as e:
            return f"❌ File not found and could not be created: {str(e)}"
    return open_application_raw("vscode", abs_path)

def open_folder_in_vscode_raw(folderpath: str) -> str:
    """Open a folder in the VS Code desktop app."""
    abs_path = folderpath if os.path.isabs(folderpath) else os.path.abspath(folderpath)
    if not os.path.isdir(abs_path):
        return f"❌ Folder not found: {folderpath}"
    return open_application_raw("vscode", abs_path)

def run_command_in_vscode_terminal_raw(command: str) -> str:
    """Focus VS Code, open the integrated terminal, and execute a command."""
    try:
        import pyautogui
    except ImportError:
        return "❌ PyAutoGUI not installed. Cannot simulate keyboard events for VS Code terminal."
        
    def focus_window(title_substring: str) -> bool:
        cmd = f"powershell -Command \"$ws = New-Object -ComObject wscript.shell; [void]$ws.AppActivate('{title_substring}')\""
        res = subprocess.run(cmd, stdin=subprocess.DEVNULL, shell=True, capture_output=True)
        return res.returncode == 0
        
    logger.info("Focusing VS Code...")
    focus_window("Visual Studio Code")
    time.sleep(1.5)
    
    logger.info("Toggling VS Code integrated terminal...")
    pyautogui.hotkey("ctrl", "`")
    time.sleep(1.5)
    
    logger.info("Typing command: %s", command)
    pyautogui.typewrite(command + "\n", interval=0.03)
    
    return f"✅ Command '{command}' sent to VS Code integrated terminal."

def search_start_menu_raw(query: str) -> list:
    """Search for applications in the Start Menu."""
    user = os.environ.get("USERPROFILE", r"C:\Users\patlo")
    dirs = [
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
        os.path.join(user, r"AppData\Roaming\Microsoft\Windows\Start Menu\Programs")
    ]
    results = []
    query = query.lower()
    for d in dirs:
        for root, _, files in os.walk(d):
            for f in files:
                if f.endswith(".lnk") and query in f.lower():
                    results.append(os.path.join(root, f))
    return results

def get_window_hwnds_raw(title_substring: str) -> list:
    import ctypes
    EnumWindows = ctypes.windll.user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    GetWindowText = ctypes.windll.user32.GetWindowTextW
    GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
    IsWindowVisible = ctypes.windll.user32.IsWindowVisible

    hwnds = []
    def foreach_window(hwnd, lParam):
        if IsWindowVisible(hwnd):
            length = GetWindowTextLength(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                GetWindowText(hwnd, buff, length + 1)
                title = buff.value
                if title_substring.lower() in title.lower():
                    hwnds.append(hwnd)
        return True

    EnumWindows(EnumWindowsProc(foreach_window), 0)
    return hwnds

def focus_application_raw(app_name: str) -> str:
    """Focus an application by bringing it to the foreground."""
    import ctypes
    hwnds = get_window_hwnds_raw(app_name)
    if not hwnds:
        return f"❌ Could not find window for '{app_name}'."
    
    hwnd = hwnds[0]
    # SW_RESTORE is 9
    ctypes.windll.user32.ShowWindow(hwnd, 9)
    ctypes.windll.user32.SetForegroundWindow(hwnd)
    return f"✅ Focused window matching '{app_name}'."

def minimize_application_raw(app_name: str) -> str:
    """Minimize an application window."""
    import ctypes
    hwnds = get_window_hwnds_raw(app_name)
    if not hwnds:
        return f"❌ Could not find window for '{app_name}'."
    
    hwnd = hwnds[0]
    # SW_MINIMIZE is 6
    ctypes.windll.user32.ShowWindow(hwnd, 6)
    return f"✅ Minimized window matching '{app_name}'."

def maximize_application_raw(app_name: str) -> str:
    """Maximize an application window."""
    import ctypes
    hwnds = get_window_hwnds_raw(app_name)
    if not hwnds:
        return f"❌ Could not find window for '{app_name}'."
    
    hwnd = hwnds[0]
    # SW_MAXIMIZE is 3
    ctypes.windll.user32.ShowWindow(hwnd, 3)
    return f"✅ Maximized window matching '{app_name}'."
