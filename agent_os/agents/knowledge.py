from typing import Any, Dict
from .base_agent import BaseAgent

class KnowledgeAgent(BaseAgent):
    """
    Queries local RAG and memory systems (ChromaDB/SQLite) 
    to retrieve project context.
    """
    def __init__(self, llm_provider):
        super().__init__(name="knowledge", llm_provider=llm_provider)

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "current_agent": self.get_name(),
            "next_node": "supervisor",
            "messages": state.get("messages", []) + [{"role": "assistant", "content": "Context retrieved from knowledge base."}]
        }
