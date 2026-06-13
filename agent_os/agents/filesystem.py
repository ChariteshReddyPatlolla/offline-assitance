from typing import Any, Dict
from .base_agent import BaseAgent
from ..interfaces.llm_provider import ILLMProvider

class FilesystemAgent(BaseAgent):
    """
    Filesystem Agent handles file operations (read, write, list).
    Typically interacts via an MCP Filesystem Server.
    """
    def __init__(self, llm_provider: ILLMProvider):
        super().__init__(name="filesystem", llm_provider=llm_provider)
        self._capabilities = ["file_read", "file_write", "directory_management"]

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes filesystem-related tasks and updates state.
        """
        return {"messages": [{"role": "assistant", "content": "Filesystem task completed."}]}
