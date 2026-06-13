from abc import ABC, abstractmethod
from typing import Any, Dict, List

class IAgent(ABC):
    """
    Abstract base class representing an autonomous agent.
    """
    
    @abstractmethod
    def get_name(self) -> str:
        """Returns the unique name of the agent."""
        pass
        
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Returns a list of capabilities this agent supports."""
        pass

    @abstractmethod
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the current LangGraph state and return state updates.
        
        Args:
            state (Dict[str, Any]): The current graph state.
            
        Returns:
            Dict[str, Any]: The updates to apply to the state.
        """
        pass
