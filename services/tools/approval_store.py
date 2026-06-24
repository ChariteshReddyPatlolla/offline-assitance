"""
Shared in-memory + DB-backed store for the approval workflow.
Sensitive tools check here before executing.
The API grants approval and re-runs the agent.
"""

import json
import logging
from typing import Optional
from functools import wraps
from langchain_core.tools import tool as lc_tool
from langchain_core.tools import StructuredTool

logger = logging.getLogger(__name__)

# Set of action_keys that have been approved by the user (in-memory fast path)
approved_actions: set = set()

# Dict of pending approvals:
# action_key -> {description, details, session_id}
pending_actions: dict = {}


def require_approval(
    action_key: str,
    description: str,
    details: dict,
    session_id: Optional[str] = None,
    force: bool = False,
) -> Optional[str]:
    """
    Check if an action is approved.

    Returns:
        None  -> Action is approved, proceed with execution.
        str   -> Approval is required; returned string becomes the tool output
                 shown in the chat UI.

    Args:
        action_key:  Unique identifier for this action
                     (e.g. "shell:pip install requests")
        description: Human-readable description shown in approval UI
        details:     Extra metadata dict, typically:
                     {
                         "command": "...",
                         "dangerous": bool,
                         "warning": "...",
                         "tool": "execute_shell_command",
                         "args": {...}
                     }
        session_id:  Chat session ID
        force:       If True, always require approval even if previously approved
    """

    # If already approved, allow execution.
    # We must ALWAYS honor an explicit user approval in the current loop.
    if action_key in approved_actions:
        approved_actions.discard(action_key)
        logger.info("Action approved: %s", action_key)
        return None

    # Store pending action
    pending_actions[action_key] = {
        "description": description,
        "details": details,
        "session_id": session_id,
    }

    logger.info("Approval required for action: %s", action_key)

    # Extract fields safely
    command = details.get("command", "")
    dangerous = details.get("dangerous", False)
    warning = details.get("warning")
    tool_name = details.get("tool")
    tool_args = details.get("args")

    # ------------------------------------------------------------------
    # IMPORTANT:
    # The FIRST line must remain exactly:
    # [NEEDS_APPROVAL:<action_key>]
    # Your frontend uses this token to detect approval requests and render
    # Yes / No buttons automatically.
    # ------------------------------------------------------------------
    message = f"[NEEDS_APPROVAL:{action_key}]\n\n"

    # Human-readable heading
    message += "## 🔐 Approval Required\n\n"

    # Description
    if description:
        message += f"### Action\n{description}\n\n"

    # Special preview for email actions
    if action_key.startswith("email:") or action_key.startswith("send_email:"):
        to_addr = details.get("to", "")
        subj = details.get("subject", "")
        email_body = details.get("body", "")
        message += (
            "### 📧 Proposed Email Draft\n"
            f"> **To:** `{to_addr}`\n"
            f"> **Subject:** *{subj}*\n"
            f"> \n"
            f"> **Body:**\n"
            f"> ```text\n"
            f"> {email_body}\n"
            f"> ```\n\n"
        )

    # Command preview (for shell commands)
    elif command:
        message += (
            "### Proposed Shell Command\n"
            f"```bash\n{command}\n```\n\n"
        )

    # Generic tool preview for non-shell tools
    elif tool_name:
        message += f"### Tool\n`{tool_name}`\n\n"

        if tool_args:
            try:
                args_json = json.dumps(tool_args, indent=2, ensure_ascii=False)
                message += (
                    "### Arguments\n"
                    f"```json\n{args_json}\n```\n\n"
                )
            except Exception:
                message += f"### Arguments\n`{tool_args}`\n\n"

    # Warning text
    if warning:
        message += f"{warning}\n\n"

    # Dangerous notice
    if dangerous:
        message += (
            "⚠️ This action has been classified as potentially destructive.\n"
            "Please review it carefully before approving.\n\n"
        )

    # Final prompt
    message += (
        "Do you want me to proceed?\n\n"
        "Use the **Approve** or **Reject** buttons below."
    )

    return message


def grant_approval(action_key: str) -> bool:
    """
    Mark an action as approved.

    Returns:
        True if the action was pending.
        False if it was not found.
    """
    was_pending = action_key in pending_actions
    approved_actions.add(action_key)
    pending_actions.pop(action_key, None)
    logger.info("Approval GRANTED for: %s", action_key)
    return was_pending


def deny_approval(action_key: str) -> bool:
    """
    Deny an action and remove it from pending approvals.

    Returns:
        True if the action was pending.
        False if it was not found.
    """
    was_pending = action_key in pending_actions
    pending_actions.pop(action_key, None)
    approved_actions.discard(action_key)
    logger.info("Approval DENIED for: %s", action_key)
    return was_pending


def revoke_pending(action_key: str):
    """
    Alias for backward compatibility.
    """
    deny_approval(action_key)


def get_pending_for_session(session_id: str) -> list:
    """
    Return all pending actions for a given session.
    """
    result = []

    for key, val in pending_actions.items():
        if val.get("session_id") == session_id or session_id is None:
            result.append(
                {
                    "action_key": key,
                    "description": val["description"],
                    "details": val["details"],
                }
            )

    return result


def get_all_pending() -> list:
    """
    Return all pending approvals.
    """
    return [
        {
            "action_key": key,
            **value,
        }
        for key, value in pending_actions.items()
    ]



def require_tool_approval(tool_obj, force: bool = False):
    """
    Wrap a tool (either a function or a LangChain BaseTool object) so that
    it requests approval before execution. Handles both sync and async tools.
    """
    from langchain_core.tools import BaseTool
    import os
    
    if isinstance(tool_obj, BaseTool):
        tool_name = tool_obj.name
        tool_description = tool_obj.description
    else:
        original_func = getattr(tool_obj, "func", tool_obj)
        tool_name = getattr(tool_obj, "name", original_func.__name__)
        tool_description = getattr(tool_obj, "description", original_func.__doc__)

    def get_action_key(*args, **kwargs):
        args_dict = kwargs.copy() if kwargs else {}
        if not args_dict and args and isinstance(args[0], str):
            args_dict["path"] = args[0]
        
        filepath = args_dict.get("filepath") or args_dict.get("path")
        if tool_name in ("write_file", "delete_file", "edit_file", "create_directory") and filepath:
            try:
                abs_path = os.path.abspath(str(filepath))
                if tool_name == "write_file":
                    return f"write:{abs_path}"
                elif tool_name == "delete_file":
                    return f"delete:{abs_path}"
                else:
                    return f"{tool_name}:{abs_path}"
            except Exception:
                pass
        return f"{tool_name}:{repr(args)}:{repr(kwargs)}"

    if isinstance(tool_obj, BaseTool):
        original_run = tool_obj._run
        original_arun = tool_obj._arun

        def check_approval(*args, **kwargs):
            args_dict = kwargs if kwargs else list(args)
            action_key = get_action_key(*args, **kwargs)
            description = f"Run tool '{tool_name}'"
            details = {
                "tool": tool_name,
                "args": args_dict,
                "dangerous": True,
            }
            
            approval_response = require_approval(
                action_key=action_key,
                description=description,
                details=details,
                force=force,
            )
            return approval_response
            
        if original_arun is not None:
            @wraps(original_arun)
            async def wrapped_arun(*args, **kwargs):
                approval_response = check_approval(*args, **kwargs)
                if approval_response is not None:
                    return approval_response
                return await original_arun(*args, **kwargs)
            tool_obj._arun = wrapped_arun
            
        @wraps(original_run)
        def wrapped_run(*args, **kwargs):
            approval_response = check_approval(*args, **kwargs)
            if approval_response is not None:
                return approval_response
            if original_run is not None:
                try:
                    return original_run(*args, **kwargs)
                except Exception:
                    pass
            if original_arun is not None:
                from services.mcp.client import run_sync
                config = kwargs.pop("config", {})
                return run_sync(original_arun(*args, config=config, **kwargs))
            raise NotImplementedError("Tool does not support sync invocation.")
        tool_obj._run = wrapped_run
        
        return tool_obj

    # Otherwise, it's a function. Fall back to existing decoration logic:
    original_func = getattr(tool_obj, "func", tool_obj)
    tool_name = getattr(tool_obj, "name", original_func.__name__)
    tool_description = getattr(tool_obj, "description", original_func.__doc__)

    @wraps(original_func)
    def _wrapped(*args, **kwargs):
        action_key = get_action_key(*args, **kwargs)
        description = f"Run tool '{tool_name}'"
        details = {
            "tool": tool_name,
            "args": kwargs if kwargs else list(args),
            "dangerous": True,
        }
        approval_response = require_approval(
            action_key=action_key,
            description=description,
            details=details,
            force=force,
        )
        if approval_response is not None:
            return approval_response
        return original_func(*args, **kwargs)

    wrapped_tool = lc_tool(_wrapped)
    wrapped_tool.name = tool_name
    wrapped_tool.description = tool_description
    return wrapped_tool