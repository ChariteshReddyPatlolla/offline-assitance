from typing import Any, Dict
from .base_agent import BaseAgent
from ..interfaces.llm_provider import ILLMProvider

class CodeGenAgent(BaseAgent):
    """
    CodeGen Agent handles writing, refactoring, and debugging code.
    """
    def __init__(self, llm_provider: ILLMProvider):
        super().__init__(name="codegen", llm_provider=llm_provider)
        self._capabilities = ["code_generation", "code_review", "debugging"]

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes code generation tasks and updates state.
        """
        return {"messages": [{"role": "assistant", "content": "CodeGen task completed."}]}
