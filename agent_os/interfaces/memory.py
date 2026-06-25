from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class IVectorMemory(ABC):
    """
    Abstract base class for Long-Term Vector Memory.
    """

    @abstractmethod
    async def store(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Stores text content and returns an ID."""
        pass

    @abstractmethod
    async def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Searches for similar content."""
        pass

    @abstractmethod
    async def delete(self, doc_id: str) -> bool:
        """Deletes a stored document."""
        pass


class IEpisodicMemory(ABC):
    """
    Abstract base class for Short-Term/Episodic Memory (LangGraph checkpointer).
    """

    @abstractmethod
    async def save_checkpoint(self, thread_id: str, state: Dict[str, Any]) -> None:
        """Saves a checkpoint of the agent state."""
        pass

    @abstractmethod
    async def load_checkpoint(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Loads the latest checkpoint for a given thread."""
        pass
