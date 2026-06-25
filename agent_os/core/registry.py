from typing import Any, Callable, Dict
from ..interfaces.agent import IAgent

class AgentRegistry:
    """Registry for managing active agents."""
    def __init__(self):
        self._agents: Dict[str, IAgent] = {}

    def register(self, agent: IAgent):
        self._agents[agent.get_name()] = agent

    def get(self, name: str) -> IAgent:
        if name not in self._agents:
            raise KeyError(f"Agent '{name}' not found in registry.")
        return self._agents[name]
        
    def list_agents(self) -> Dict[str, IAgent]:
        return self._agents


class ToolRegistry:
    """Registry for managing local python tools available to agents."""
    def __init__(self):
        self._tools: Dict[str, Callable] = {}

    def register(self, name: str, func: Callable):
        self._tools[name] = func

    def get(self, name: str) -> Callable:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found in registry.")
        return self._tools[name]
        
    def execute(self, name: str, **kwargs) -> Any:
        tool = self.get(name)
        return tool(**kwargs)
        
    def list_tools(self) -> Dict[str, Callable]:
        return self._tools
