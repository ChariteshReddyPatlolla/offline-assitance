import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from mcp.server.fastmcp import FastMCP
from services.tools.impl.browser import (
    open_url_in_browser_raw,
    search_youtube_raw,
    web_search_raw,
    pause_playback_raw,
    resume_playback_raw,
    browser_navigate_raw,
    browser_click_raw,
    browser_type_raw,
    browser_wait_for_raw,
    browser_take_screenshot_raw,
    browser_close_raw,
    browser_scroll_raw,
    browser_extract_text_raw,
    list_browser_tabs_raw,
    switch_browser_tab_raw
)

mcp = FastMCP("browser")

@mcp.tool()
def open_url_in_browser(url: str) -> str:
    """Opens a URL in the persistent browser."""
    return open_url_in_browser_raw(url)

@mcp.tool()
def search_youtube(query: str) -> str:
    """Searches YouTube and plays the first video result."""
    return search_youtube_raw(query)

@mcp.tool()
def web_search(query: str) -> str:
    """Search the web for current or general information using DuckDuckGo."""
    return web_search_raw(query)

@mcp.tool()
def pause_playback() -> str:
    """Pauses video or audio playback on the active browser tab."""
    return pause_playback_raw()

@mcp.tool()
def resume_playback() -> str:
    """Resumes video or audio playback on the active browser tab."""
    return resume_playback_raw()

@mcp.tool()
def browser_navigate(url: str) -> str:
    """Navigate to a URL using the active persistent browser tab."""
    return browser_navigate_raw(url)

@mcp.tool()
def browser_click(selector: str) -> str:
    """Click an element on the active persistent browser tab."""
    return browser_click_raw(selector)

@mcp.tool()
def browser_type(selector: str, text: str) -> str:
    """Type text into an input element on the active persistent browser tab."""
    return browser_type_raw(selector, text)

@mcp.tool()
def browser_wait_for(selector: str) -> str:
    """Wait for an element to be visible on the active persistent browser tab."""
    return browser_wait_for_raw(selector)

@mcp.tool()
def browser_take_screenshot(path: str) -> str:
    """Take a screenshot of the active persistent browser tab."""
    return browser_take_screenshot_raw(path)

@mcp.tool()
def browser_close() -> str:
    """Close the active persistent browser tab and process gracefully."""
    return browser_close_raw()

@mcp.tool()
def browser_scroll(direction: str = "down", amount: int = 500) -> str:
    """Scroll the active persistent browser page.
    Args:
        direction: 'down', 'up', 'left', or 'right'.
        amount: number of pixels to scroll.
    """
    return browser_scroll_raw(direction, amount)

@mcp.tool()
def browser_extract_text() -> str:
    """Extract all visible text content from the active browser page."""
    return browser_extract_text_raw()

@mcp.tool()
def list_browser_tabs() -> str:
    """Lists all open tabs in the persistent browser and indicates the active one."""
    return list_browser_tabs_raw()

@mcp.tool()
def switch_browser_tab(index: int) -> str:
    """Switches the active browser tab to the given index."""
    return switch_browser_tab_raw(index)

if __name__ == "__main__":
    mcp.run()
