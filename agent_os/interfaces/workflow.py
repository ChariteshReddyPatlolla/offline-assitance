from abc import ABC, abstractmethod
from typing import Any, Dict

class IWorkflowEngine(ABC):
    """
    Abstract base class representing a Graph Workflow Engine (e.g., LangGraph wrapper).
    """

    @abstractmethod
    def build_graph(self) -> Any:
        """Compiles and builds the state graph."""
        pass

    @abstractmethod
    async def run(self, initial_state: Dict[str, Any], thread_id: str) -> Dict[str, Any]:
        """
        Executes the workflow graph.
        """
        pass
