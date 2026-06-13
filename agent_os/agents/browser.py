import json
from typing import Any, Dict
from .base_agent import BaseAgent
from shared.context import current_session_id
from services.session_manager import session_manager

class BrowserAgent(BaseAgent):
    """
    Interacts with the Persistent Playwright MCP Server to navigate websites, 
    fill forms, and seamlessly synchronize with the Session Manager.
    """
    def __init__(self, llm_provider):
        super().__init__(name="browser", llm_provider=llm_provider)
        self._capabilities = [
            "browser_navigate", "browser_click", "browser_fill", 
            "browser_press", "browser_get_state", "browser_close"
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
You are the Persistent Browser Agent, an expert at web automation using Playwright.

[CURRENT SESSION STATE]
{json.dumps(context_state, indent=2)}

You are controlling a SINGLE persistent browser tab. Do NOT open new tabs unless absolutely necessary.
If the user asks to "Search for X", "Play video", or "Stop", you must deduce the context based on `current_url` and `current_browser_session` from the session state.

Your Capabilities (MCP Tools):
1. **browser_navigate(url)**: Navigate the current tab to a URL.
2. **browser_click(selector)**: Click an element (e.g., 'text=Play', 'button#submit').
3. **browser_fill(selector, text)**: Type text into an input.
4. **browser_press(key)**: Press a key (e.g., 'Enter', 'Space').
5. **browser_get_state()**: Get the live URL and title of the active tab.
6. **browser_close()**: Close the persistent browser.

Output your execution plan, call the appropriate tools (using `name`, `parameters`).
After taking an action that changes the page (like navigating or searching), you MUST output an updated `context_state` JSON block at the end setting `current_url` and `current_browser_session`.
"""

        try:
            response = await self._llm_provider.generate(
                prompt=target_task,
                system_prompt=system_prompt,
                tools=self._capabilities
            )
            
            # Simulated tool execution logic would route to executor
            return {
                "current_agent": self.get_name(),
                "next_node": "executor_agent",
                "messages": state.get("messages", []) + [{"role": "assistant", "content": response}]
            }
        except Exception as e:
            return {
                "current_agent": self.get_name(),
                "next_node": "END",
                "messages": state.get("messages", []) + [{"role": "assistant", "content": f"Failed to process Browser command: {str(e)}"}]
            }
