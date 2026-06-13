import json
from typing import Any, Dict
from .base_agent import BaseAgent
from shared.context import current_session_id
from services.session_manager import session_manager

class VSCodeAgent(BaseAgent):
    """
    Dedicated VSCode Agent for code editing, creation, execution, and debugging inside VS Code.
    Synchronizes tightly with the Session State to maintain context across turns.
    """
    def __init__(self, llm_provider):
        super().__init__(name="vscode", llm_provider=llm_provider)
        self._capabilities = [
            "open_project", "open_file", "create_file", "write_code", 
            "read_code", "modify_code", "run_code", "debug_code"
        ]

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        session_id = current_session_id.get()
        context_state = {}
        if session_id:
            context_state = session_manager.get_session_state(session_id)

        target_task = ""
        pending_tasks = state.get("pending_tasks", [])
        if pending_tasks:
            target_task = pending_tasks[0].get("description", "")
        else:
            messages = state.get("messages", [])
            if messages:
                target_task = messages[-1].get("content", "")

        system_prompt = f"""
You are the VSCode Agent, an expert developer operating natively within the user's VS Code environment.

[CURRENT SESSION STATE]
{json.dumps(context_state, indent=2)}

You MUST implicitly use the 'current_file' and 'current_directory' from the session state if the user says "this file", "the file", "open it", "run it", "fix the bug", "add an endpoint", etc. You do not need to ask the user to repeat the file name.

Your Capabilities & Execution Rules:
1. **Open project**: Use `open_in_vscode` with the directory path.
2. **Open file**: Use `open_in_vscode` with the file path. Ensure you update `current_file` in context_state JSON block.
3. **Create/Write/Modify code**: Use filesystem tools (`write_file`, `read_file`). Always update `current_file` in context_state if working on a new file.
4. **Run/Debug code**: Use `run_code_in_vscode_terminal` to execute the current file dynamically.

Output your execution plan, call the appropriate tools (using `name`, `parameters`), and if you change the active file, output an updated context_state JSON block at the end.
"""

        try:
            # Generate the response using the unified LLM provider
            response = await self._llm_provider.generate(
                prompt=target_task,
                system_prompt=system_prompt,
                tools=["open_in_vscode", "run_code_in_vscode_terminal", "read_file", "write_file"]
            )
            
            # Parse mock tools for execution
            pending_tasks = state.get("pending_tasks", [])
            task_id = f"task_{len(pending_tasks)+1}"
            
            # Very basic extraction logic or just pass a mock task to test the execution engine
            pending_tasks.append({
                "task_id": task_id,
                "description": "Execute VSCode actions",
                "tool_name": "shell_execute",
                "tool_parameters": {"command": "echo 'VSCode actions executed'"},
                "status": "pending",
                "dependencies": [],
                "max_retries": 1
            })
            
            return {
                "current_agent": self.get_name(),
                "next_node": "execution_agent", # Send tool calls to the executor
                "pending_tasks": pending_tasks,
                "messages": state.get("messages", []) + [{"role": "assistant", "content": response}]
            }
        except Exception as e:
            return {
                "current_agent": self.get_name(),
                "next_node": "END",
                "messages": state.get("messages", []) + [{"role": "assistant", "content": f"Failed to process VSCode command: {str(e)}"}]
            }
