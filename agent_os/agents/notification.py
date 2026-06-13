from typing import Any, Dict
from .base_agent import BaseAgent

class NotificationAgent(BaseAgent):
    """
    Handles asynchronous alerts, emails, and OS-level notifications to the user.
    """
    def __init__(self, llm_provider):
        super().__init__(name="notification", llm_provider=llm_provider)

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "current_agent": self.get_name(),
            "next_node": "supervisor",
            "messages": state.get("messages", []) + [{"role": "assistant", "content": "Notification dispatched."}]
        }
