"""
Shared in-memory + DB-backed store for the approval workflow.
Sensitive tools check here before executing.
The API grants approval and re-runs the agent.
"""
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Set of action_keys that have been approved by the user (in-memory fast path)
approved_actions: set = set()

# Dict of pending approvals: action_key -> {description, details, session_id}
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
    - Returns None  -> action is approved, proceed with execution.
    - Returns str   -> approval needed; the string is returned as the tool result.

    Args:
        action_key:   Unique identifier for this action (e.g. "shell:pip install x")
        description:  Human-readable description shown in the approval card
        details:      Extra info dict (stored for display)
        session_id:   Chat session ID for routing the approval card
        force:        If True, always require approval (cannot be bypassed by prior approval)
    """
    if not force and action_key in approved_actions:
        approved_actions.discard(action_key)
        logger.info("Action approved (pre-approved): %s", action_key)
        return None  # Proceed

    # Register as pending
    pending_actions[action_key] = {
        "description": description,
        "details": details,
        "session_id": session_id,
    }
    logger.info("Approval required for action: %s", action_key)

    return (
        f"[NEEDS_APPROVAL:{action_key}] "
        f"**Action Requested:**\n\n"
        f"{description}\n\n"
        f"This action requires your explicit approval before I can execute it. "
        f"Please respond with **Yes** or **No** using the approval buttons that should appear in the chat."
    )


def grant_approval(action_key: str) -> bool:
    """Mark an action as approved. Returns True if it was pending."""
    was_pending = action_key in pending_actions
    approved_actions.add(action_key)
    pending_actions.pop(action_key, None)
    logger.info("Approval GRANTED for: %s", action_key)
    return was_pending


def deny_approval(action_key: str) -> bool:
    """Remove a pending approval without approving. Returns True if it was pending."""
    was_pending = action_key in pending_actions
    pending_actions.pop(action_key, None)
    approved_actions.discard(action_key)
    logger.info("Approval DENIED for: %s", action_key)
    return was_pending


def revoke_pending(action_key: str):
    """Alias kept for backward compatibility."""
    deny_approval(action_key)


def get_pending_for_session(session_id: str) -> list:
    """Return all pending actions for a given session_id."""
    result = []
    for key, val in pending_actions.items():
        if val.get("session_id") == session_id or session_id is None:
            result.append({
                "action_key": key,
                "description": val["description"],
                "details": val["details"],
            })
    return result


def get_all_pending() -> list:
    """Return all pending actions."""
    return [
        {"action_key": k, **v}
        for k, v in pending_actions.items()
    ]
