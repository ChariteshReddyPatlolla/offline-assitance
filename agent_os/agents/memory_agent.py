from typing import Any, Dict
from .base_agent import BaseAgent
from ..interfaces.llm_provider import ILLMProvider
from ..memory.sqlite_db import SQLiteMemory
from ..memory.rag_pipeline import RAGPipeline

class MemoryAgent(BaseAgent):
    """
    Background agent responsible for summarizing chat logs into dense semantic memories
    and extracting user preferences from ongoing execution.
    """
    def __init__(self, llm_provider: ILLMProvider, sql_memory: SQLiteMemory, rag_pipeline: RAGPipeline):
        super().__init__(name="memory_agent", llm_provider=llm_provider)
        self.sql = sql_memory
        self.rag = rag_pipeline
        self._capabilities = ["summarization", "preference_extraction", "memory_consolidation"]

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes the current state, looking for large chat histories to summarize.
        """
        # In a real system, this is triggered when conversation history > N tokens
        messages = state.get("messages", [])
        if len(messages) > 10:
            # 1. Summarize
            summary_prompt = "Summarize the following interaction, extracting key architectural decisions and user preferences:\n" + str(messages[-10:])
            summary = await self.llm.generate(summary_prompt, system_prompt="You are a memory consolidation expert.")
            
            # 2. Ingest into Chroma as semantic insight
            self.rag.ingest_raw_text(
                text=summary,
                source_metadata={"type": "conversation_summary", "session_id": state.get("session_id", "default")}
            )
            
            # 3. Clean state
            state["messages"] = messages[:-10] + [{"role": "system", "content": f"Previous conversation summarized: {summary}"}]
            
        return {
            "current_agent": self.get_name(),
            "next_node": "supervisor",
            "messages": state.get("messages", [])
        }
