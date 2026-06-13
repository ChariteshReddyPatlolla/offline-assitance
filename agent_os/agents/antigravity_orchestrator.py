import asyncio
import logging
from typing import Any, Dict
from .base_agent import BaseAgent
from ..interfaces.llm_provider import ILLMProvider
from ..integrations.antigravity import AntigravityController, PromptGenerator, ResponseAnalyzer, OutputValidator

logger = logging.getLogger(__name__)

class AntigravityOrchestratorAgent(BaseAgent):
    """
    Manages the Antigravity integration, treating Antigravity as a worker agent.
    Loops over tasks, prompts Antigravity, and validates output continuously.
    """
    def __init__(self, llm_provider: ILLMProvider):
        super().__init__(name="antigravity_orchestrator", llm_provider=llm_provider)
        self.controller = AntigravityController()
        self.prompt_generator = PromptGenerator()
        self.analyzer = ResponseAnalyzer()
        self.validator = OutputValidator()
        self.max_retries = 3

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        execution_plan = state.get("execution_plan", {})
        messages = state.get("messages", [])
        
        if not execution_plan or "tasks" not in execution_plan:
            return {
                "current_agent": self.get_name(),
                "next_node": "END",
                "messages": messages + [{"role": "assistant", "content": "No execution plan found for Orchestrator to run."}]
            }

        tasks = execution_plan.get("tasks", [])
        
        # Ensure Antigravity is open
        if not self.controller.is_open:
            await self.controller.open_antigravity()

        content_log = "Orchestrating Antigravity...\n"
        
        # Execute tasks sequentially or logically based on DAG 
        # (For simplicity here, we iterate through tasks in order)
        for idx, task in enumerate(tasks):
            task_id = task.get("task_id", f"Task_{idx}")
            content_log += f"\n**Running {task_id}**\n"
            
            prompt = self.prompt_generator.generate_prompt(task, context=state)
            
            success = False
            attempts = 0
            
            while not success and attempts < self.max_retries:
                attempts += 1
                await self.controller.send_prompt(prompt)
                
                raw_response = await self.controller.read_response()
                analysis = self.analyzer.analyze(raw_response)
                
                if self.validator.validate(analysis, task):
                    success = True
                    content_log += f"- Attempt {attempts}: Success! Task validated.\n"
                else:
                    content_log += f"- Attempt {attempts}: Failed. Feedback: {analysis.feedback}\n"
                    # Reprompt on failure
                    prompt = f"Previous attempt failed. Feedback: {analysis.feedback}\nPlease fix the errors and complete: {task.get('description')}"
            
            if not success:
                content_log += f"-> Task {task_id} failed after {self.max_retries} attempts. Halting orchestrator.\n"
                break

        await self.controller.close_antigravity()
        content_log += "\nOrchestration complete."

        return {
            "current_agent": self.get_name(),
            "next_node": "END",
            "messages": messages + [{"role": "assistant", "content": content_log}]
        }
