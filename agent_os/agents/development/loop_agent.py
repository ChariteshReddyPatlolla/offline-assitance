import logging
from typing import Any, Dict
from ..base_agent import BaseAgent
from ...interfaces.llm_provider import ILLMProvider
from ...integrations.antigravity.controller import AntigravityController
from .executor import TaskExecutor
from .validation import ValidationEngine
from .retry import RetryManager

logger = logging.getLogger(__name__)

class DevelopmentLoop(BaseAgent):
    """
    Agent Node that encapsulates the Autonomous Development Loop over an Execution DAG.
    """
    def __init__(self, llm_provider: ILLMProvider):
        super().__init__(name="development_loop", llm_provider=llm_provider)
        self.controller = AntigravityController()
        self.executor = TaskExecutor(self.controller)
        self.validator = ValidationEngine()
        self.retry_manager = RetryManager(self.controller, max_retries=3)

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        execution_plan = state.get("execution_plan", {})
        messages = state.get("messages", [])
        
        if not execution_plan or "tasks" not in execution_plan:
            return {
                "current_agent": self.get_name(),
                "next_node": "END",
                "messages": messages + [{"role": "assistant", "content": "No execution plan found for Development Loop."}]
            }

        tasks = execution_plan.get("tasks", [])
        results = state.get("execution_results", {})
        
        if not self.controller.is_open:
            await self.controller.open_antigravity()

        content_log = "## Autonomous Development Loop Initialized\n\n"
        
        for idx, task in enumerate(tasks):
            task_id = task.get("task_id", f"Task_{idx}")
            if task_id in results and results[task_id].get("status") == "success":
                continue # Skip already successful tasks
                
            content_log += f"**Executing: {task_id}**\n"
            
            # Step 1-3: Generate prompt, send, receive code
            raw_code = await self.executor.execute_task(task, context=state)
            
            # Step 4: Validate code
            validation = self.validator.validate(raw_code, task)
            
            success = validation.is_valid
            
            # If validation fails, loop using RetryManager
            while not success:
                content_log += f"- Validation failed: {validation.feedback}\n"
                try:
                    raw_code = await self.retry_manager.generate_fix_and_retry(task, validation.feedback)
                    validation = self.validator.validate(raw_code, task)
                    success = validation.is_valid
                except Exception as e:
                    content_log += f"- {str(e)}\n"
                    break
                    
            # Step 5: Store results
            if success:
                content_log += f"- Status: \u2705 Success\n\n"
                results[task_id] = {"status": "success", "output": raw_code}
            else:
                content_log += f"- Status: \u274c Failed after retries.\n\n"
                results[task_id] = {"status": "failed", "output": raw_code}
                break # Halt loop on failure
                
        await self.controller.close_antigravity()
        content_log += "Development loop cycle completed."

        return {
            "current_agent": self.get_name(),
            "next_node": "END",
            "execution_results": results,
            "messages": messages + [{"role": "assistant", "content": content_log}]
        }
