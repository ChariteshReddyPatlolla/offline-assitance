from typing import Dict, Any
from .manager import PermissionManager

class ApprovalEngine:
    """
    Handles the escalation workflow when HIGH or CRITICAL actions are blocked.
    """
    def __init__(self, permission_manager: PermissionManager):
        self.manager = permission_manager

    def format_approval_request(self, block_result: Dict[str, Any], tool_name: str, parameters: Dict[str, Any]) -> str:
        """
        Formats a clear user-facing message requesting explicit permission.
        """
        risk_level = block_result.get("risk").name
        scope = block_result.get("scope")
        
        request = f"[Approval Required]\n"
        request += f"\u26a0\ufe0f **Risk Level:** {risk_level}\n"
        request += f"**Action:** `{tool_name}`\n"
        if "command" in parameters:
            request += f"**Command:** `{parameters['command']}`\n"
        request += "\nThis action requires your explicit permission to proceed. Please reply with 'yes' to approve or 'no' to cancel."
        
        return request
        
    def process_user_response(self, user_response: str, pending_scope: str) -> bool:
        """
        Parses user input to determine if the pending scope is approved.
        """
        response_lower = user_response.lower().strip()
        if response_lower in ["yes", "y", "approve", "proceed", "ok"]:
            self.manager.grant_permission(pending_scope)
            return True
        return False
