import asyncio
import logging
import sys
import os
import atexit
import threading
from typing import Dict, List, Any
from langchain_mcp_adapters.client import MultiServerMCPClient
from services.mcp.config import MCP_SERVERS

logger = logging.getLogger(__name__)

# Keep a global dictionary of running clients to keep their subprocesses alive
_running_clients = {}

def run_sync(coro):
    """
    Runs an async coroutine synchronously. If an event loop is already running in
    the current thread, executes it in a separate thread with its own loop to
    prevent event loop collisions and deadlocks.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        result = []
        error = []
        def target():
            try:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                res = new_loop.run_until_complete(coro)
                result.append(res)
            except Exception as e:
                error.append(e)
            finally:
                new_loop.close()
        t = threading.Thread(target=target)
        t.start()
        t.join()
        if error:
            raise error[0]
        return result[0]
    else:
        return asyncio.run(coro)


class MCPClientManager:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        global _running_clients
        self.clients = _running_clients
        # Register a global exit handler to kill child processes
        atexit.register(self.shutdown_all)

    def get_client(self, name: str) -> MultiServerMCPClient:
        """Retrieve or initialize the client for the specified server name."""
        if name not in MCP_SERVERS:
            raise ValueError(f"Unknown MCP server configuration: '{name}'")

        if name in self.clients:
            return self.clients[name]

        config = MCP_SERVERS[name]
        logger.info("Initializing MCP client process for '%s'...", name)
        try:
            # MultiServerMCPClient manages the subprocess stdio transport internally
            client = MultiServerMCPClient({name: config})
            self.clients[name] = client
            return client
        except Exception as e:
            logger.error("Failed to initialize client for '%s': %s", name, e)
            raise e

    async def aget_tools(self, name: str) -> List[Any]:
        """Fetch discovered tools from the server, with retry logic on failure."""
        client = self.get_client(name)
        try:
            return await client.get_tools()
        except Exception as e:
            logger.warning("Error fetching tools for '%s' (%s). Resetting and retrying...", name, e)
            self.clients.pop(name, None)
            client = self.get_client(name)
            return await client.get_tools()

    async def acall_tool(self, server_name: str, tool_name: str, **kwargs) -> Any:
        """Execute a tool call against the server with connection recovery."""
        client = self.get_client(server_name)
        try:
            tools = await client.get_tools()
            for t in tools:
                if t.name == tool_name:
                    return await t.ainvoke(kwargs)
            raise ValueError(f"Tool '{tool_name}' not found on server '{server_name}'.")
        except Exception as e:
            logger.warning("Tool call '%s' failed on '%s' (%s). Restarting server...", tool_name, server_name, e)
            self.clients.pop(server_name, None)
            client = self.get_client(server_name)
            tools = await client.get_tools()
            for t in tools:
                if t.name == tool_name:
                    return await t.ainvoke(kwargs)
            raise e

    def get_tools(self, name: str) -> List[Any]:
        """Synchronously get all tools for a server."""
        return run_sync(self.aget_tools(name))

    def call_tool(self, server_name: str, tool_name: str, **kwargs) -> Any:
        """Synchronously execute a tool call against a server."""
        return run_sync(self.acall_tool(server_name, tool_name, **kwargs))

    def shutdown_all(self):
        """Cleanup all processes on shutdown."""
        if self.clients:
            logger.info("Cleaning up and shutting down active MCP processes...")
            # MultiServerMCPClient handles closing subprocesses when dereferenced,
            # but we explicitly clear the dictionary to trigger cleanup.
            self.clients.clear()


async def load_mcp_tools() -> list:
    """
    Discovers all tools across all configured MCP servers.
    Provides backward compatibility for import-time registration.
    """
    manager = MCPClientManager.get_instance()
    all_tools = []
    
    for name in MCP_SERVERS.keys():
        logger.info("Auto-loading tools from server '%s'...", name)
        try:
            tools = await manager.aget_tools(name)
            all_tools.extend(tools)
            logger.info("Successfully discovered %d tools from '%s'", len(tools), name)
        except Exception as e:
            logger.error("Skipping MCP server '%s' due to loading failure: %s", name, e)
            
    return all_tools
