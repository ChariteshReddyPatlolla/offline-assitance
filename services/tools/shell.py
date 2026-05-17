import os
import subprocess
import logging
from langchain_core.tools import tool

from services.tools.approval_store import require_approval
from services.tools.safety import (
    should_require_shell_approval,
    should_force_reapproval,
    is_dangerous_command,
    get_safety_warning,
)

logger = logging.getLogger(__name__)


# ============================================================================
# SHELL COMMAND TOOL
# ============================================================================

@tool
def execute_shell_command(command: str) -> str:
    """
    Execute a shell command on the local machine.

    Security Policy:
    - EVERY shell command requires explicit user approval.
    - The exact command is shown in the chat.
    - Dangerous commands are clearly flagged.
    - Dangerous commands always require fresh approval.

    Use cases:
    - Running Python scripts
    - Installing packages
    - Checking system information
    - Running git commands
    - Executing OS commands
    """

    if not command or not command.strip():
        return "❌ No shell command provided."

    command = command.strip()

    # Analyze command safety
    dangerous = is_dangerous_command(command)
    warning = get_safety_warning(command)

    # Require approval for every shell command
    if should_require_shell_approval(command):
        approval = require_approval(
            action_key=f"shell:{command[:200]}",
            description=(
                f"{'⚠️ **DANGEROUS COMMAND**\n\n' if dangerous else ''}"
                f"Run shell command:\n"
                f"```bash\n{command}\n```"
            ),
            details={
                "command": command,
                "dangerous": dangerous,
                "warning": warning,
            },
            force=should_force_reapproval(command),
        )

        # If approval is required, return the approval message.
        # The command will execute only after the user approves.
        if approval:
            return approval

    # Execute after approval
    try:
        logger.info("Executing shell command: %s", command)

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=os.getcwd(),
        )

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()

        sections = []

        if stdout:
            sections.append(stdout)

        if stderr:
            sections.append(f"Errors:\n{stderr}")

        if not sections:
            if result.returncode == 0:
                return "✅ Command executed successfully with no output."
            return f"❌ Command failed with exit code {result.returncode}."

        output = "\n\n".join(sections)

        # Limit huge outputs to avoid flooding the chat.
        max_chars = 12000
        if len(output) > max_chars:
            output = (
                output[:max_chars]
                + "\n\n[Output truncated because it was too large.]"
            )

        if result.returncode != 0:
            return (
                f"❌ Command exited with code {result.returncode}.\n\n"
                f"{output}"
            )

        return output

    except subprocess.TimeoutExpired:
        logger.warning("Shell command timed out: %s", command)
        return "❌ Command timed out after 120 seconds."

    except Exception as e:
        logger.exception("Error executing shell command")
        return f"❌ Error executing command: {str(e)}"


# ============================================================================
# BROWSER TOOL
# ============================================================================

@tool
def open_url_in_browser(url: str) -> str:
    """
    Opens a URL in Google Chrome.

    Examples:
    - open youtube.com
    - open github.com
    - open google.com
    """

    if not url or not url.strip():
        return "❌ No URL provided."

    url = url.strip()

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        from services.tools.browser import _open_in_chrome

        _open_in_chrome(url)
        return f"✅ Opened '{url}' in Google Chrome."

    except Exception as e:
        logger.exception("Error opening URL")
        return f"❌ Error opening browser: {str(e)}"


# ============================================================================
# YOUTUBE SEARCH TOOL
# ============================================================================

@tool
def search_youtube(query: str) -> str:
    """
    Searches YouTube for a query, opens the first video,
    and starts playback automatically.

    Examples:
    - play lofi music
    - play Taylor Swift
    - play relaxing music on youtube
    """

    if not query or not query.strip():
        return "❌ No YouTube search query provided."

    try:
        from services.tools.browser import search_youtube as _yt
        return _yt.invoke({"query": query.strip()})

    except Exception as e:
        logger.exception("Error searching YouTube")
        return f"❌ Error searching YouTube: {str(e)}"


# ============================================================================
# WEB SEARCH TOOL
# ============================================================================

@tool
def web_search(query: str) -> str:
    """
    Search the web for information and return structured results.

    Use this for:
    - Facts
    - Tutorials
    - News
    - Documentation
    """

    if not query or not query.strip():
        return "❌ No search query provided."

    try:
        from services.tools.browser import web_search as _ws
        return _ws.invoke({"query": query.strip()})

    except Exception as e:
        logger.exception("Error performing web search")
        return f"❌ Error performing web search: {str(e)}"
    
    