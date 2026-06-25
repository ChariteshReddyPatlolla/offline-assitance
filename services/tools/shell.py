import os
from langchain_core.tools import tool
from services.tools.approval_store import require_approval
from shared.context import active_session_dir
from services.tools.safety import (
    should_require_shell_approval,
    should_force_reapproval,
    is_dangerous_command,
    get_safety_warning,
)
from services.mcp.client import MCPClientManager

@tool
def execute_shell_command(command: str) -> str:
    """
    Execute a shell command on the local machine.
    """
    if not command or not command.strip():
        return "❌ No shell command provided."

    command = command.strip()

    if any(op in command for op in ["&&", ";", "||", "\n"]):
        return (
            "❌ Shell command chaining is NOT allowed. Please break down the task "
            "and execute only the first immediate subcommand without combining it with other commands."
        )

    dangerous = is_dangerous_command(command)
    warning = get_safety_warning(command)

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
        if approval:
            return approval

    # Invoke tool on the shell MCP server
    return MCPClientManager.get_instance().call_tool(
        "shell", "execute_shell_command", command=command
    )

@tool
def open_url_in_browser(url: str) -> str:
    """
    Opens a URL in Google Chrome/Brave.
    """
    if not url or not url.strip():
        return "❌ No URL provided."
    return MCPClientManager.get_instance().call_tool(
        "browser", "open_url_in_browser", url=url.strip()
    )

@tool
def search_youtube(query: str) -> str:
    """
    Searches YouTube for a query, opens the first video, and starts playback.
    """
    if not query or not query.strip():
        return "❌ No YouTube search query provided."
    return MCPClientManager.get_instance().call_tool(
        "browser", "search_youtube", query=query.strip()
    )

@tool
def web_search(query: str) -> str:
    """
    Search the web for information and return structured results.
    """
    if not query or not query.strip():
        return "❌ No search query provided."
    return MCPClientManager.get_instance().call_tool(
        "browser", "web_search", query=query.strip()
    )