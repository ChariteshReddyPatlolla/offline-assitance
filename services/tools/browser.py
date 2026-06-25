from langchain_core.tools import tool
from services.mcp.client import MCPClientManager

@tool
def pause_playback() -> str:
    """
    Pauses video or audio playback on the active YouTube or browser tab.
    """
    return MCPClientManager.get_instance().call_tool(
        "browser", "pause_playback"
    )

@tool
def resume_playback() -> str:
    """
    Resumes video or audio playback on the active YouTube or browser tab.
    """
    return MCPClientManager.get_instance().call_tool(
        "browser", "resume_playback"
    )

@tool
def browser_navigate(url: str) -> str:
    """
    Navigate to a URL using the active persistent browser tab.
    Args:
        url: The website URL to open.
    """
    return MCPClientManager.get_instance().call_tool(
        "browser", "browser_navigate", url=url
    )

@tool
def browser_click(selector: str) -> str:
    """
    Click an element on the active persistent browser tab.
    Args:
        selector: The CSS selector of the element to click.
    """
    return MCPClientManager.get_instance().call_tool(
        "browser", "browser_click", selector=selector
    )

@tool
def browser_type(selector: str, text: str) -> str:
    """
    Type text into an input element on the active persistent browser tab.
    Args:
        selector: The CSS selector of the input field.
        text: The text to type.
    """
    return MCPClientManager.get_instance().call_tool(
        "browser", "browser_type", selector=selector, text=text
    )

@tool
def browser_wait_for(selector: str) -> str:
    """
    Wait for an element to be visible on the active persistent browser tab.
    Args:
        selector: The CSS selector to wait for.
    """
    return MCPClientManager.get_instance().call_tool(
        "browser", "browser_wait_for", selector=selector
    )

@tool
def browser_take_screenshot(path: str) -> str:
    """
    Take a screenshot of the active persistent browser tab.
    Args:
        path: The absolute path where the screenshot will be saved.
    """
    return MCPClientManager.get_instance().call_tool(
        "browser", "browser_take_screenshot", path=path
    )

@tool
def browser_close() -> str:
    """
    Close the active persistent browser tab and process gracefully.
    """
    return MCPClientManager.get_instance().call_tool(
        "browser", "browser_close"
    )

@tool
def browser_scroll(direction: str = "down", amount: int = 500) -> str:
    """
    Scroll the active persistent browser page.
    Args:
        direction: 'down', 'up', 'left', or 'right'.
        amount: number of pixels to scroll.
    """
    return MCPClientManager.get_instance().call_tool(
        "browser", "browser_scroll", direction=direction, amount=amount
    )

@tool
def browser_extract_text() -> str:
    """
    Extract all visible text/content from the active browser page.
    """
    return MCPClientManager.get_instance().call_tool(
        "browser", "browser_extract_text"
    )

@tool
def list_browser_tabs() -> str:
    """
    Lists all open tabs in the persistent browser and indicates the active one.
    """
    return MCPClientManager.get_instance().call_tool(
        "browser", "list_browser_tabs"
    )

@tool
def switch_browser_tab(index: int) -> str:
    """
    Switches the active browser tab to the given index.
    Args:
        index: The index of the tab to switch to.
    """
    return MCPClientManager.get_instance().call_tool(
        "browser", "switch_browser_tab", index=index
    )