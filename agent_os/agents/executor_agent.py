from typing import Any, Dict
from .base_agent import BaseAgent
from ..interfaces.llm_provider import ILLMProvider
from ..core.executor import ExecutorEngine
from ..core.models import PlannedTask

class ExecutionAgent(BaseAgent):
    """
    Executes specific tool actions defined by the Planner, 
    leveraging the ExecutorEngine for safety and verifiability.
    """
    def __init__(self, llm_provider: ILLMProvider, executor_engine: ExecutorEngine):
        super().__init__(name="execution_agent", llm_provider=llm_provider)
        self.executor_engine = executor_engine
        self._capabilities = ["tool_execution", "validation", "rollback"]

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pulls a pending task from the state and executes it via the ExecutorEngine.
        """
        pending_tasks = state.get("pending_tasks", [])
        if not pending_tasks:
            return {"next_node": "supervisor", "current_agent": self.get_name()}

        # Grab the first available task (In a real system, the graph routes a specific task)
        task_data = pending_tasks.pop(0)
        task = PlannedTask(**task_data) # Re-hydrate model

        success = await self.executor_engine.execute_task(task)

        if success:
            state.setdefault("completed_tasks", []).append(task_data)
        else:
            # Trigger rollback if the task utterly failed
            await self.executor_engine.rollback()
            state["error"] = f"Task {task.task_id} failed. Rollback executed."
            
        return {
            "next_node": "supervisor",
            "current_agent": self.get_name(),
            "pending_tasks": pending_tasks,
            "completed_tasks": state.get("completed_tasks", [])
        }
