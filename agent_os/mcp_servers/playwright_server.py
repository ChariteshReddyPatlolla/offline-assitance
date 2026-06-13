from mcp.server.fastmcp import FastMCP
from playwright.sync_api import sync_playwright
import json

mcp = FastMCP("Playwright")

# Global state to keep the browser persistent across tool calls
_playwright = None
_browser = None
_context = None
_page = None

def get_page():
    global _playwright, _browser, _context, _page
    if _page is None:
        _playwright = sync_playwright().start()
        # Launch browser in non-headless mode to see actions
        _browser = _playwright.chromium.launch(headless=False)
        _context = _browser.new_context()
        _page = _context.new_page()
    return _page

@mcp.tool()
def browser_navigate(url: str) -> str:
    """Navigates the browser to the specified URL in the same tab."""
    page = get_page()
    page.goto(url)
    return f"Navigated to {url}"

@mcp.tool()
def browser_click(selector: str) -> str:
    """Clicks on a specific element identified by a CSS selector or text. You can use text locators like 'text=Play'."""
    page = get_page()
    page.click(selector)
    return f"Clicked on {selector}"

@mcp.tool()
def browser_fill(selector: str, text: str) -> str:
    """Types text into an input field identified by a CSS selector."""
    page = get_page()
    page.fill(selector, text)
    return f"Filled {selector} with '{text}'"

@mcp.tool()
def browser_press(key: str) -> str:
    """Presses a keyboard key (e.g., 'Enter', 'Space', 'Escape')."""
    page = get_page()
    page.keyboard.press(key)
    return f"Pressed key {key}"

@mcp.tool()
def browser_get_state() -> str:
    """Returns the current URL and Title to synchronize with Session Manager."""
    if _page is None:
        return '{"url": "", "title": ""}'
    return json.dumps({
        "url": _page.url,
        "title": _page.title()
    })

@mcp.tool()
def browser_close() -> str:
    """Explicitly closes the active browser session."""
    global _playwright, _browser, _context, _page
    if _browser:
        _browser.close()
        _playwright.stop()
        _playwright = None
        _browser = None
        _context = None
        _page = None
        return "Browser session closed."
    return "No active browser session to close."

if __name__ == "__main__":
    mcp.run()
