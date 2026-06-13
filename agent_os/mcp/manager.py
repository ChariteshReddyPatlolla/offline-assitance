import asyncio
import logging
from typing import Dict, List, Any
from ..interfaces.mcp_client import IMCPClient
from .registry import MCPRegistry

logger = logging.getLogger(__name__)

class MCPManager:
    """
    Manages connections to multiple MCP servers.
    Provides capability discovery, health checks, and automatic reconnection.
    """
    def __init__(self, registry: MCPRegistry):
        self.registry = registry
        self._clients: Dict[str, IMCPClient] = {}
        self._health_tasks: Dict[str, asyncio.Task] = {}
        self._capabilities: Dict[str, List[Dict[str, Any]]] = {}

    async def initialize_all(self):
        """Connects to all servers listed in the registry."""
        await self.registry.load_config()
        servers = self.registry.list_servers()
        for name, config in servers.items():
            # In a real implementation, we instantiate the specific IMCPClient implementation
            # client = StdioMCPClient(config)
            # await self.connect_server(name, client)
            pass

    async def connect_server(self, name: str, client: IMCPClient):
        """Connects, discovers capabilities, and starts health checks."""
        try:
            logger.info(f"Connecting to MCP server: {name}")
            await client.connect("")  # Stdio usually doesn't need URL, config is passed in client init
            self._clients[name] = client
            
            # Capability Discovery
            tools = await client.list_tools()
            self._capabilities[name] = tools
            logger.info(f"Discovered {len(tools)} tools from {name}")
            
            # Start Health Check
            if name in self._health_tasks:
                self._health_tasks[name].cancel()
            self._health_tasks[name] = asyncio.create_task(self._health_check_loop(name, client))
            
        except Exception as e:
            logger.error(f"Failed to connect to {name}: {e}. Retrying in background...")
            asyncio.create_task(self._reconnect_loop(name, client))

    async def _health_check_loop(self, name: str, client: IMCPClient):
        """Periodically pings the server to ensure health."""
        while True:
            await asyncio.sleep(30) # Check every 30 seconds
            try:
                # Ping implies a basic lightweight request, e.g., list_tools
                await client.list_tools()
            except Exception as e:
                logger.warning(f"Health check failed for {name}: {e}. Initiating reconnection...")
                await self._reconnect_loop(name, client)
                break

    async def _reconnect_loop(self, name: str, client: IMCPClient):
        """Attempts exponential backoff reconnection."""
        attempt = 1
        while attempt <= 5:
            await asyncio.sleep(2 ** attempt)
            logger.info(f"Reconnecting to {name} (Attempt {attempt})...")
            try:
                await client.connect("")
                logger.info(f"Reconnected successfully to {name}")
                self._health_tasks[name] = asyncio.create_task(self._health_check_loop(name, client))
                return
            except Exception:
                attempt += 1
        logger.error(f"Exhausted reconnection attempts for {name}. Server marked dead.")

    async def reload_hot(self):
        """Checks for registry changes and connects new servers dynamically."""
        if await self.registry.load_config():
            servers = self.registry.list_servers()
            for name, config in servers.items():
                if name not in self._clients:
                    logger.info(f"Hot loading new server: {name}")
                    # client = StdioMCPClient(config)
                    # await self.connect_server(name, client)
                    pass

    def get_client(self, name: str) -> IMCPClient:
        return self._clients.get(name)

    def list_all_capabilities(self) -> Dict[str, List[Dict[str, Any]]]:
        return self._capabilities
