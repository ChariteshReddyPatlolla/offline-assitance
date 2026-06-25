import logging
from typing import Any, Dict
from ...integrations.antigravity.controller import AntigravityController

logger = logging.getLogger(__name__)

class TaskExecutor:
    """
    Executes tasks by formulating an implementation prompt and using the AntigravityController.
    """
    def __init__(self, controller: AntigravityController):
        self.controller = controller

    async def execute_task(self, task: Dict[str, Any], context: Dict[str, Any] = None) -> str:
        """
        Generates an implementation prompt and runs it in Antigravity.
        """
        task_id = task.get("task_id", "unknown_task")
        description = task.get("description", "Perform the assigned task.")
        
        prompt = f"""[DEVELOPMENT LOOP PROMPT]
Task ID: {task_id}
Task Details: {description}

Please write the necessary implementation for this task. 
Do not await user input. Run all necessary tools to implement this task completely.
"""
        if context and context.get("architecture"):
            prompt += f"\nArchitecture Constraints: {context.get('architecture').get('architecture', '')}"
            
        logger.info(f"TaskExecutor: Sending implementation prompt for {task_id}")
        await self.controller.send_prompt(prompt)
        
        raw_code_response = await self.controller.read_response()
        return raw_code_response
