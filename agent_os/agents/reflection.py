from typing import Any, Dict
from .base_agent import BaseAgent
from ..interfaces.llm_provider import ILLMProvider
from ..core.recovery import FailureAnalyzer, RecoveryEngine
from ..core.models import PlannedTask

class ReflectionAgent(BaseAgent):
    """
    Triggers when a task fails. It diagnoses the failure, queries historical recovery 
    patterns, drafts a fix, and resubmits the task for execution if confident.
    """
    def __init__(self, llm_provider: ILLMProvider, failure_analyzer: FailureAnalyzer, recovery_engine: RecoveryEngine):
        super().__init__(name="reflection", llm_provider=llm_provider)
        self.analyzer = failure_analyzer
        self.engine = recovery_engine

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        pending_tasks = state.get("pending_tasks", [])
        if not pending_tasks:
            return {"next_node": "supervisor", "current_agent": self.get_name(), "messages": state.get("messages", [])}
            
        # Analyze the top task (assuming it failed)
        failed_task_dict = pending_tasks[0]
        # Hydrate to pydantic for type safety or use directly
        task = PlannedTask(**failed_task_dict)
        
        error_msg = task.result or "Unknown failure"
        
        # 1. Diagnose
        analysis = await self.analyzer.analyze(error_message=error_msg, context=task.description)
        task.failure_reason = analysis.get("root_cause", "Unknown")
        task.confidence_score = analysis.get("confidence_score", 0.0)
        
        messages = state.get("messages", [])
        
        # 2. Decide if we can recover
        if task.confidence_score > 60.0 and task.retry_count < 3:
            # 3. Draft Recovery
            recovery_plan = await self.engine.draft_recovery_plan(task, analysis)
            
            task.retry_count += 1
            task.status = "pending" # Reset for execution
            task.recovery_attempts.append(recovery_plan)
            
            messages.append({"role": "assistant", "content": f"Reflection complete. Recovery plan generated for {task.task_id}."})
            
            # Update state with the mutated task
            pending_tasks[0] = task.model_dump()
            
            # Send back to coding or automation based on capabilities
            next_node = "coding" if "code" in str(task.required_capabilities) else "supervisor"
            
            return {
                "next_node": next_node,
                "current_agent": self.get_name(),
                "pending_tasks": pending_tasks,
                "messages": messages
            }
        else:
            # Escalation to user
            task.status = "blocked"
            pending_tasks[0] = task.model_dump()
            messages.append({"role": "assistant", "content": f"Task {task.task_id} blocked. Escalate to user. Reason: {task.failure_reason}"})
            
            return {
                "next_node": "notification",
                "current_agent": self.get_name(),
                "pending_tasks": pending_tasks,
                "messages": messages
            }
