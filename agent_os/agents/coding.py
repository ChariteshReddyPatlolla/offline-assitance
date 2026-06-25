from typing import Any, Dict
from .base_agent import BaseAgent

from services.session_manager import session_manager

class CodingAgent(BaseAgent):
    """
    Handles writing, debugging, and testing code.
    Outputs tool execution requests for filesystem/shell.
    """
    def __init__(self, llm_provider):
        super().__init__(name="coding", llm_provider=llm_provider)
        self._capabilities = ["write_file", "execute_shell_command", "read_file", "delete_file"]

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        pending_tasks = state.get("pending_tasks", [])
        if pending_tasks:
            target_task = pending_tasks[0].get("description", "")
        else:
            messages = state.get("messages", [])
            target_task = messages[-1].get("content", "") if messages else "No task"

        # 1. Query Workspace RAG
        context_snippets = []
        try:
            if hasattr(session_manager, "indexer") and session_manager.indexer:
                res = session_manager.indexer.vector_store.query_memory(
                    collection_name="project_rag",
                    query_texts=[target_task],
                    n_results=5
                )
                if res and res.get("documents") and res["documents"][0]:
                    context_snippets = res["documents"][0]
        except Exception as e:
            pass # Collection might not exist or error

        rag_context = "\n\n---\n".join(context_snippets) if context_snippets else "No project context available."

        system_prompt = f"""
You are the expert Coding Agent.
Your job is to generate code, modify files, and run commands.

[WORKSPACE CONTEXT (from RAG)]
{rag_context}

Use this context to ensure you are aligning with the current architecture, existing APIs, and symbols.
Output your tool calls (e.g. write_file) to implement the request.
Output "END" when you are completely finished with the task to trigger a review.
"""
        try:
            response = await self._llm_provider.generate(
                prompt=target_task,
                system_prompt=system_prompt,
                tools=self._capabilities
            )
            
            if response.strip() == "END":
                return {
                    "current_agent": self.get_name(),
                    "next_node": "critic",
                    "messages": state.get("messages", []) + [{"role": "assistant", "content": "Code generated."}]
                }
                
            return {
                "current_agent": self.get_name(),
                "next_node": "executor_agent",
                "messages": state.get("messages", []) + [{"role": "assistant", "content": response}]
            }
        except Exception as e:
            return {
                "current_agent": self.get_name(),
                "next_node": "critic",
                "messages": state.get("messages", []) + [{"role": "assistant", "content": f"Failed to generate code: {str(e)}"}]
            }
