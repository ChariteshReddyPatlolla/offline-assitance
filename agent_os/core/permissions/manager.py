from typing import Dict, Any, List
from .classifier import RiskClassifier, RiskLevel
import logging

logger = logging.getLogger(__name__)

class PermissionManager:
    """
    Manages session grants and determines if an action can proceed automatically.
    """
    def __init__(self):
        self.granted_scopes: List[str] = []

    def check_permission(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates risk. Returns a dict indicating if execution is allowed or blocked.
        """
        risk_level = RiskClassifier.evaluate(tool_name, parameters)
        
        # Scope definition for session grants (e.g. tracking specific commands)
        action_scope = f"{tool_name}:{parameters.get('command', '')}"
        
        if risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]:
            return {"allowed": True, "risk": risk_level}
            
        if action_scope in self.granted_scopes:
            logger.info(f"PermissionManager: Auto-approving previously granted scope: {action_scope}")
            return {"allowed": True, "risk": risk_level}
            
        # Escalation required
        return {
            "allowed": False, 
            "risk": risk_level, 
            "scope": action_scope,
            "reason": f"{risk_level.name} risk detected for action '{tool_name}'."
        }

    def grant_permission(self, scope: str):
        """
        Records a user's approval for a specific scope for the session.
        """
        if scope not in self.granted_scopes:
            self.granted_scopes.append(scope)
            logger.info(f"PermissionManager: Granted scope -> {scope}")
