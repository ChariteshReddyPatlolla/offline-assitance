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

# Create a sleek, narrow vertical chat window that floats on top by default!
window = webview.create_window(
    title='OmniAgent Copilot',
    url=url,
    width=400,          # Perfect width for a floating sidebar chat
    height=750,         # Tall vertical format
    on_top=True,        # KEEP FLOATING ON TOP!
    resizable=True,
    text_select=True
)

webview.start()
