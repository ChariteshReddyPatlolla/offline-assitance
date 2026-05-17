import os
import subprocess
import webbrowser
import urllib.parse
import logging
from langchain_core.tools import tool
from services.tools.approval_store import require_approval
from services.tools.safety import is_dangerous_command, get_safety_warning

logger = logging.getLogger(__name__)


@tool
def execute_shell_command(command: str) -> str:
    """
    Execute a shell command on the local machine.
    Use this for running scripts, checking system info, or performing OS tasks.
    ALWAYS REQUIRES USER APPROVAL before executing.
    """
    warning = get_safety_warning(command)
    is_dangerous = is_dangerous_command(command)
    prefix = "⚠️ **DANGEROUS COMMAND** — " if is_dangerous else ""

    action_key = f"shell:{command[:80]}"
    approval = require_approval(
        action_key=action_key,
        description=f"{prefix}Run shell command:\n```\n{command}\n```",
        details={"command": command, "dangerous": is_dangerous, "warning": warning},
        force=is_dangerous,  # Dangerous commands always force re-approval
    )
    if approval:
        return approval

    try:
        logger.info("Executing shell command: %s", command)
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=60
        )
        output = result.stdout
        if result.stderr:
            output += f"\nErrors:\n{result.stderr}"
        return output.strip() if output.strip() else "Command executed successfully with no output."
    except subprocess.TimeoutExpired:
        return "❌ Command timed out after 60 seconds."
    except Exception as e:
        return f"❌ Error executing command: {str(e)}"


@tool
def open_url_in_browser(url: str) -> str:
    """
    Opens a URL in the user's default web browser.
    Use this when the user asks to open a website or navigate to a URL.
    Examples: 'open youtube.com', 'go to github.com', 'open google'
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        from services.tools.browser import _open_in_chrome
        _open_in_chrome(url)
        return f"✅ Opened '{url}' in Google Chrome."
    except Exception as e:
        return f"❌ Error opening browser: {str(e)}"


@tool
def search_youtube(query: str) -> str:
    """
    Searches YouTube for a query, opens the first video, and starts playback automatically.
    Use this when the user wants to play music, watch a video, or search YouTube.
    Examples: 'play lofi music', 'play Taylor Swift', 'play relaxing music on youtube'
    """
    # Delegate to the browser tool's full implementation
    from services.tools.browser import search_youtube as _yt
    return _yt.invoke({"query": query})


@tool
def web_search(query: str) -> str:
    """
    Search the web for information and return structured results.
    Use this to look up facts, tutorials, news, or any information.
    """
    from services.tools.browser import web_search as _ws
    return _ws.invoke({"query": query})
