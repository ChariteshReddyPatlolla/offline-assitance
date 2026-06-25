import logging
from typing import Any, Dict
from ...integrations.antigravity.controller import AntigravityController

logger = logging.getLogger(__name__)

class RetryManager:
    """
    Manages task retries and generates targeted fix prompts for the Antigravity worker.
    """
    def __init__(self, controller: AntigravityController, max_retries: int = 3):
        self.controller = controller
        self.max_retries = max_retries
        self.attempts: Dict[str, int] = {}

    def get_attempts(self, task_id: str) -> int:
        return self.attempts.get(task_id, 0)

    async def generate_fix_and_retry(self, task: Dict[str, Any], feedback: str) -> str:
        """
        Generates a targeted fix prompt based on validation feedback and resubmits it.
        """
        task_id = task.get("task_id", "unknown_task")
        current_attempts = self.attempts.get(task_id, 0)
        
        if current_attempts >= self.max_retries:
            raise Exception(f"Max retries ({self.max_retries}) exceeded for task {task_id}")
            
        self.attempts[task_id] = current_attempts + 1
        
        prompt = f"""[DEVELOPMENT LOOP - CORRECTION REQUIRED]
Task ID: {task_id}
Previous attempt failed validation.

Feedback from ValidationEngine:
{feedback}

Please carefully fix the identified issues and try again.
"""
        logger.info(f"RetryManager: Sending fix prompt for {task_id} (Attempt {self.attempts[task_id]}/{self.max_retries})")
        
        await self.controller.send_prompt(prompt)
        return await self.controller.read_response()
