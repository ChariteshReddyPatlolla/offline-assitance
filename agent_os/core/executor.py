import asyncio
from typing import Any, Dict, List
import logging
from .models import PlannedTask, ValidationCriteria, RollbackAction
from .registry import ToolRegistry
from .permissions import RiskClassifier, RiskLevel, PermissionManager, ApprovalEngine

logger = logging.getLogger(__name__)

class ExecutorEngine:
    """
    Executes planned tasks with validation, retries, and rollback capabilities.
    Uses the Command Pattern to maintain a rollback stack.
    """
    def __init__(self, tool_registry: ToolRegistry, permission_manager: PermissionManager):
        self.tool_registry = tool_registry
        self.permission_manager = permission_manager
        self.approval_engine = ApprovalEngine(permission_manager)
        self.rollback_stack: List[RollbackAction] = []

    async def execute_task(self, task: PlannedTask) -> bool:
        """
        Executes a task. Validates the result. Retries on failure. 
        Records rollback action if successful.
        """
        attempt = 0
        while attempt <= task.max_retries:
            try:
                # 0. Check Approval Gates
                check_result = self.permission_manager.check_permission(task.tool_name, task.tool_parameters)
                
                if not check_result["allowed"]:
                    # In a real async flow with human-in-the-loop, this would block
                    # For testing we assume False so we can see block logic, or True if we want auto
                    req_msg = self.approval_engine.format_approval_request(
                        check_result, task.tool_name, task.tool_parameters
                    )
                    logger.info(f"PROMPTING USER: {req_msg}")
                    # Simulate user response "yes" for testing unblocking, but normally this yields.
                    is_approved = self.approval_engine.process_user_response("yes", check_result["scope"])
                    
                    if not is_approved:
                        logger.warning(f"Task {task.task_id} blocked: Missing user approval.")
                        return False
                        
                elif check_result["risk"] == RiskLevel.MEDIUM:
                    logger.info(f"Auto-executing MEDIUM risk action: {task.tool_name}")
                
                # 1. Execute the main tool
                logger.info(f"Executing {task.task_id}: {task.tool_name} (Attempt {attempt+1})")
                self.tool_registry.execute(task.tool_name, **task.tool_parameters)
                
                # 2. Validate Post-Conditions
                if task.validation:
                    if not self._validate(task.validation):
                        raise Exception(f"Validation failed for {task.task_id}")
                
                # 3. Success! Add to rollback stack
                if task.rollback:
                    self.rollback_stack.append(task.rollback)
                    
                return True
                
            except Exception as e:
                logger.warning(f"Task {task.task_id} failed: {e}")
                attempt += 1
                if attempt <= task.max_retries:
                    await asyncio.sleep(2 ** attempt) # Exponential backoff
                else:
                    logger.error(f"Task {task.task_id} exhausted retries.")
                    return False

    def _validate(self, validation: ValidationCriteria) -> bool:
        """Executes the validation check tool."""
        try:
            return self.tool_registry.execute(validation.check_type, **validation.parameters)
        except Exception:
            return False

    async def rollback(self):
        """
        Executes inverse actions for all previously successful tasks in reverse order.
        """
        logger.warning("Initiating rollback sequence...")
        while self.rollback_stack:
            action = self.rollback_stack.pop()
            try:
                logger.info(f"Rolling back: {action.tool_name}")
                self.tool_registry.execute(action.tool_name, **action.parameters)
            except Exception as e:
                logger.error(f"Critical failure during rollback of {action.tool_name}: {e}")
                # In a production system, this might trigger human escalation or persistent state repair
