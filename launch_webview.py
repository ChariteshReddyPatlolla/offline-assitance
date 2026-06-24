import webview
import sys
import time

url = 'http://localhost:5173'
if len(sys.argv) > 1:
    url = sys.argv[1]

print("==================================================")
print(f"  Launching OmniAgent Floating WebView...")
print(f"  Target: {url}")
print("==================================================")

class Api:
    def set_compact_mode(self, is_compact):
        try:
            import ctypes
            user32 = ctypes.windll.user32
            screen_width = user32.GetSystemMetrics(0)
            screen_height = user32.GetSystemMetrics(1)
            
            if is_compact:
                # Resize to small bar and move to bottom middle
                width = 600
                height = 80
                x = (screen_width - width) // 2
                y = screen_height - height - 60 # 60px from bottom (above taskbar)
                window.resize(width, height)
                window.move(x, y)
            else:
                # Restore to normal size, right side
                width = 400
                height = 750
                x = screen_width - width - 40
                y = (screen_height - height) // 2
                window.resize(width, height)
                window.move(x, y)
        except Exception as e:
            print("Resize error:", e)

api = Api()

# Create a sleek, narrow vertical chat window that floats on top by default!
window = webview.create_window(
    title='OmniAgent Copilot',
    url=url,
    width=400,          # Perfect width for a floating sidebar chat
    height=750,         # Tall vertical format
    on_top=True,        # KEEP FLOATING ON TOP!
    resizable=True,
    text_select=True,
    frameless=False,
    transparent=False,
    js_api=api
)

webview.start()
