from abc import ABC, abstractmethod
from typing import Any, Dict, List

class IMCPClient(ABC):
    """
    Abstract base class for an MCP (Model Context Protocol) Client.
    """

    @abstractmethod
    async def connect(self, server_url: str) -> bool:
        """Connects to the specified MCP server."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnects from the MCP server."""
        pass

    @abstractmethod
    async def list_tools(self) -> List[Dict[str, Any]]:
        """Lists available tools from the connected MCP server."""
        pass

    @abstractmethod
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """
        Executes a specific tool on the MCP server.
        """
        pass
        
    @abstractmethod
    async def list_resources(self) -> List[Dict[str, Any]]:
        """Lists available resources from the MCP server."""
        pass
        
    @abstractmethod
    async def read_resource(self, uri: str) -> Any:
        """Reads a specific resource from the MCP server."""
        pass
