from typing import Any, Dict, List
from ..interfaces.agent import IAgent
from ..interfaces.llm_provider import ILLMProvider

class BaseAgent(IAgent):
    """
    Base implementation for all specialized agents.
    Provides common utilities for interacting with the LLM provider.
    """
    
    def __init__(self, name: str, llm_provider: ILLMProvider):
        self._name = name
        self._llm_provider = llm_provider
        self._capabilities: List[str] = []

    def get_name(self) -> str:
        return self._name
        
    def get_capabilities(self) -> List[str]:
        return self._capabilities

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Default processing loop. Specialized agents should override this.
        """
        return {"messages": [{"role": "assistant", "content": f"Default processing by {self._name}."}]}
