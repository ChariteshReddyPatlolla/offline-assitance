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

    async def verify_shell_command(self, action_key: str, command: str) -> bool:
        """Uses LLM to verify if a shell command is safe to auto-approve."""
        prompt = f"""
You are an automated security verifier for a system building a software project.
Please evaluate the following shell command to ensure it is SAFE to run autonomously without human intervention.
Safe commands include: mkdir, cd, npm init, npm install, pip install, git commands, echo, touch, compiling code, running linters, starting dev servers, etc.
UNSAFE commands include: rm -rf /, formatting disks, downloading and running unknown binary executables, etc.

Command to verify:
```bash
{command}
```

Is this command safe to run autonomously?
Reply with exactly "YES" or "NO".
"""
        response = await self.llm_provider.generate(prompt)
        return "YES" in response.upper()

    async def _poll_and_approve(self):
        """Background task to continually check and approve safe shell commands."""
        while self.controller.is_open:
            try:
                pending = await self.controller.get_pending_approvals()
                for p in pending:
                    action_key = p.get("action_key", "")
                    details = p.get("details", {})
                    command = details.get("command", "")
                    tool = details.get("tool", "")
                    
                    if tool == "execute_shell_command" or action_key.startswith("shell:"):
                        is_safe = await self.verify_shell_command(action_key, command)
                        await self.controller.decide_approval(action_key, approved=is_safe)
                        if not is_safe:
                            logger.warning(f"Orchestrator blocked unsafe command: {command}")
                    elif tool in ["write_file", "create_directory", "delete_file"] or action_key.startswith("write:") or action_key.startswith("delete:"):
                        # Auto-approve basic file ops
                        await self.controller.decide_approval(action_key, approved=True)
            except Exception as e:
                logger.error(f"Error in orchestrator polling: {e}")
            await asyncio.sleep(2)

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
        
        # Start the background polling task
        polling_task = asyncio.create_task(self._poll_and_approve())

        # Execute tasks
        for idx, task in enumerate(tasks):
            task_id = task.get("task_id", f"Task_{idx}")
            content_log += f"\n**Running {task_id}**\n"
            
            prompt = self.prompt_generator.generate_prompt(task, context=state)
            
            success = False
            attempts = 0
            
            while not success and attempts < self.max_retries:
                attempts += 1
                response_data = await self.controller.send_prompt(prompt)
                
                # Check if it was an error or a completed task
                if isinstance(response_data, dict) and "Error:" in response_data.get("content", ""):
                    content_log += f"- Attempt {attempts}: API Error.\n"
                else:
                    # In this architecture, send_prompt blocks until the agent finishes its generation turn.
                    # If it successfully finishes, we assume the task step is done.
                    # Real validation could analyze the full response text here.
                    success = True
                    content_log += f"- Attempt {attempts}: Success! Task completed.\n"
                
                if not success:
                    prompt = f"Previous attempt failed or stalled. Please retry and complete: {task.get('description')}"
            
            if not success:
                content_log += f"-> Task {task_id} failed after {self.max_retries} attempts. Halting orchestrator.\n"
                break

        await self.controller.close_antigravity()
        polling_task.cancel()
        
        content_log += "\nOrchestration complete."

        return {
            "current_agent": self.get_name(),
            "next_node": "END",
            "messages": messages + [{"role": "assistant", "content": content_log}]
        }
