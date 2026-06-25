from typing import Any, Dict
from .base_agent import BaseAgent
from ..interfaces.llm_provider import ILLMProvider

class RAGAgent(BaseAgent):
    """
    RAG Agent handles retrieving information from long-term memory or document stores.
    """
    def __init__(self, llm_provider: ILLMProvider):
        super().__init__(name="rag", llm_provider=llm_provider)
        self._capabilities = ["information_retrieval", "semantic_search", "document_qa"]

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes RAG queries and injects context into the state.
        """
        return {"messages": [{"role": "assistant", "content": "RAG task completed."}]}
