import os
import subprocess
import webbrowser
import time
import shutil
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


@tool
def close_application(app_name: str) -> str:
    """
    Closes a desktop application or specific window by its name or title.
    Use this when the user asks to "close" or "stop" a program, browser, or website (like YouTube).
    Examples: 'youtube', 'chrome', 'notepad', 'vscode', 'calculator'
    """
    import subprocess
    name_lower = app_name.lower().strip()
    
    # Check if we are trying to close YouTube or a browser tab
    if "youtube" in name_lower or "yt" in name_lower:
        # 1. Close ONLY the automated persistent browser page cleanly
        try:
            from services.tools.browser import close_persistent_browser
            if close_persistent_browser():
                return "✅ Closed the automated YouTube persistent browser window."
            else:
                return "ℹ️ No automated YouTube session was active. I've left your personal Brave tabs completely untouched!"
        except Exception as e:
            return f"❌ Error trying to close YouTube: {str(e)}"
            
    # Standard application process names
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
    
    # Try graceful main window close first via PowerShell
    cmd_graceful = f'powershell -Command "Get-Process -Name \'{executable}\' -ErrorAction SilentlyContinue | ForEach-Object {{ $_.CloseMainWindow() }}"'
    try:
        subprocess.run(cmd_graceful, shell=True, capture_output=True, text=True)
        # Check if the process still exists
        cmd_check = f'powershell -Command "Get-Process -Name \'{executable}\' -ErrorAction SilentlyContinue"'
        check_res = subprocess.run(cmd_check, shell=True, capture_output=True, text=True)
        if not check_res.stdout.strip():
            return f"✅ Closed '{app_name}' gracefully."
    except Exception:
        pass
        
    # Fallback to taskkill if graceful close didn't work or failed
    try:
        subprocess.run(f"taskkill /IM {executable}.exe /F", shell=True, capture_output=True, text=True)
        subprocess.run(f"taskkill /IM {executable} /F", shell=True, capture_output=True, text=True)
        return f"✅ Closed '{app_name}' successfully."
    except Exception as e:
        return f"❌ Could not close '{app_name}'. Error: {str(e)}"


@tool
def run_editor_sync_demo() -> str:
    """
    Natively automates the complete visual VS Code and Notepad editor synchronization demo:
    1. Creates `agent_demo` folder on Desktop (supporting OneDrive redirections).
    2. Opens `agent_demo` workspace folder and an empty main.py inside VS Code.
    3. Types `print("Hello from VS Code")` in real-time inside the active VS Code window and saves it.
    4. Opens the same main.py in Notepad.
    5. Types the updated contents (`print("Hello from Notepad")` & metadata) in real-time inside Notepad, saves, and closes Notepad.
    6. Returns focus to VS Code.
    7. Toggles the integrated terminal via the Ctrl+` hotkey.
    8. Types "python main.py" to execute the script in real-time.
    9. Closes files, terminal tabs, and exit VS Code window gracefully.
    10. Deletes the agent_demo folder from the Desktop after a generous display period.
    """
    # Robust Desktop Path detection (including OneDrive redirections)
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

    # Prevent pyautogui fail-safe from aborting the script on tiny mouse movements
    pyautogui.FAILSAFE = False

    # Win32 Window Focus activation helper via native PowerShell ComObject
    def focus_window(title_substring: str):
        cmd = f"powershell -Command \"$ws = New-Object -ComObject wscript.shell; [void]$ws.AppActivate('{title_substring}')\""
        subprocess.run(cmd, shell=True, capture_output=True)
        time.sleep(1.5)

    print("[OmniAgent Demo] Step 1: Creating agent_demo folder on Desktop...")
    os.makedirs(demo_dir, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("")  # Create empty main.py so it appears in the editor immediately
    time.sleep(2)

    print("[OmniAgent Demo] Step 2: Launching VS Code with workspace folder and file...")
    # Open both workspace folder and main.py file in a single atomic invocation
    subprocess.Popen(["cmd", "/c", "start", "", "code", demo_dir, file_path], shell=False)
    time.sleep(12)  # Give VS Code ample time to load all plugins and workspaces

    print("[OmniAgent Demo] Step 3: Typing 'Hello from VS Code' in real-time...")
    focus_window("Visual Studio Code")
    focus_window("main.py")
    
    # Select all and delete to start fresh
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.5)
    pyautogui.press("backspace")
    time.sleep(0.5)
    
    # Dynamically type code inside VS Code
    pyautogui.typewrite('print("Hello from VS Code")\n', interval=0.03)
    time.sleep(1)
    
    # Save the file
    pyautogui.hotkey("ctrl", "s")
    time.sleep(2)

    print("[OmniAgent Demo] Step 4: Opening main.py in Notepad...")
    subprocess.Popen(["cmd", "/c", "start", "", "notepad", file_path], shell=False)
    time.sleep(4)

    print("[OmniAgent Demo] Step 5: Replacing contents via Notepad typing...")
    focus_window("Notepad")
    focus_window("main.py - Notepad")
    
    # Select all and delete
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.5)
    pyautogui.press("backspace")
    time.sleep(0.5)
    
    # Type new code lines inside Notepad
    pyautogui.typewrite('print("Hello from Notepad")\nprint("This file was edited by the OmniAgent")\n', interval=0.03)
    time.sleep(1.5)
    
    # Save Notepad file and close it
    pyautogui.hotkey("ctrl", "s")
    time.sleep(1.5)
    pyautogui.hotkey("alt", "f4")
    time.sleep(2.5)

    print("[OmniAgent Demo] Step 6 & 7: Return to VS Code and toggle integrated terminal...")
    focus_window("Visual Studio Code")
    focus_window("main.py")
    time.sleep(1.5)
    
    # Open Integrated Terminal
    pyautogui.hotkey("ctrl", "`")
    time.sleep(3.5)  # Wait for shell terminal window to focus and initialize

    print("[OmniAgent Demo] Step 8: Typing python command to run main.py...")
    pyautogui.typewrite("python main.py\n", interval=0.03)
    time.sleep(10)  # Wait 10 seconds to allow the user to watch the output execute perfectly

    print("[OmniAgent Demo] Step 9: Cleaning up VS Code terminal, tabs, and editor window...")
    pyautogui.hotkey("ctrl", "`")  # Toggle terminal closed
    time.sleep(1.5)
    pyautogui.hotkey("ctrl", "w")  # Close file tab
    time.sleep(1.5)
    
    # Close VS Code gracefully
    focus_window("Visual Studio Code")
    pyautogui.hotkey("alt", "f4")
    time.sleep(4.5)

    print("[OmniAgent Demo] Step 10: Cleaning up Desktop directory...")
    time.sleep(3)  # Let user verify final state before directory removal
    try:
        shutil.rmtree(demo_dir)
        print("[OmniAgent Demo] Desktop folder deleted successfully!")
    except Exception as e_del:
        print(f"[OmniAgent Demo] Folder deletion warning: {str(e_del)}")

    return (
        "✅ Visual VS Code and Notepad synchronization workflow demo executed successfully!\n"
        "Created workspace, synchronized edits in real-time, executed in terminal, and cleaned up."
    )



