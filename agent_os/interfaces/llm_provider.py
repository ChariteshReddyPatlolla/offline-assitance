from abc import ABC, abstractmethod
from typing import Any, Dict
from pydantic import BaseModel

class ILLMProvider(ABC):
    """
    Abstract base class for LLM providers (e.g., Ollama).
    """

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        """
        Generate a freeform text response.
        """
        pass
        
    @abstractmethod
    async def generate_structured(self, prompt: str, schema: BaseModel, system_prompt: str = "") -> BaseModel:
        """
        Generate a structured response adhering to a given Pydantic schema.
        """
        pass

    @abstractmethod
    async def stream(self, prompt: str, system_prompt: str = "") -> Any:
        """
        Stream a text response.
        """
        pass
