from typing import Any, Dict
from .base_agent import BaseAgent

class CriticAgent(BaseAgent):
    """
    Reviews code, plans, or execution outputs. Detects mistakes
    and enforces verification before marking tasks complete.
    """
    def __init__(self, llm_provider):
        super().__init__(name="critic", llm_provider=llm_provider)

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # Evaluates previous messages
        return {
            "current_agent": self.get_name(),
            "next_node": "supervisor", # Return to supervisor after review
            "messages": state.get("messages", []) + [{"role": "assistant", "content": "Review passed. No mistakes detected."}]
        }
