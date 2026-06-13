import contextvars
import ctypes
import time
import threading
import logging

logger = logging.getLogger(__name__)

# Thread-safe and async-safe request context variables to store the active session state
active_session_dir = contextvars.ContextVar("active_session_dir", default=None)
active_session_file = contextvars.ContextVar("active_session_file", default=None)
current_session_id = contextvars.ContextVar("current_session_id", default=None)

# Global store for cancellation requests
cancel_requests = set()

# Global variables for real-time window tracking
last_active_window_title = "Desktop"
last_active_app_name = "Desktop"
_tracker_started = False
_tracker_lock = threading.Lock()

def start_window_tracker():
    global _tracker_started
    with _tracker_lock:
        if _tracker_started:
            return
        _tracker_started = True

    def tracker_loop():
        global last_active_window_title, last_active_app_name
        user32 = ctypes.windll.user32
        
        logger.info("OmniAgent active window tracker thread started.")
        while True:
            try:
                hwnd = user32.GetForegroundWindow()
                if hwnd:
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buff, length + 1)
                        title = buff.value
                        
                        # Filter out chat webview and developer consoles/terminals
                        title_lower = title.lower()
                        ignored_keywords = [
                            "omniagent", "antigravity", "command prompt", 
                            "windows powershell", "cmd.exe", "powershell.exe", 
                            "start.bat", "start-desktop.bat", "start-floating-chat.bat",
                            "fastapi", "npm run dev", "vite", "python"
                        ]
                        
                        if title and not any(kw in title_lower for kw in ignored_keywords):
                            last_active_window_title = title
                            
                            # Determine app name from title
                            if "visual studio code" in title_lower or "vs code" in title_lower or " - code" in title_lower:
                                last_active_app_name = "VS Code"
                            elif "notepad" in title_lower:
                                last_active_app_name = "Notepad"
                            elif any(b in title_lower for b in ["chrome", "brave", "edge", "firefox", "browser", "youtube"]):
                                last_active_app_name = "Browser"
                            else:
                                last_active_app_name = title.split(" - ")[-1] if " - " in title else title
            except Exception:
                pass
            time.sleep(0.5)

    t = threading.Thread(target=tracker_loop, daemon=True)
    t.start()

