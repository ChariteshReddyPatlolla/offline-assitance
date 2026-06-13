import json
import os
import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class MCPRegistry:
    """
    Monitors a configuration file to dynamically register MCP servers.
    Supports hot loading: if the file changes, it can trigger a reload.
    """
    def __init__(self, config_path: str):
        self.config_path = config_path
        self._last_mtime = 0
        self.servers_config: Dict[str, Any] = {}

    async def load_config(self) -> bool:
        """
        Loads the config. Returns True if changes were detected (Hot Loading).
        """
        if not os.path.exists(self.config_path):
            logger.warning(f"MCP config not found at {self.config_path}")
            return False

        current_mtime = os.path.getmtime(self.config_path)
        if current_mtime > self._last_mtime:
            logger.info("Changes detected in MCP configuration. Reloading...")
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.servers_config = data.get("mcpServers", {})
            self._last_mtime = current_mtime
            return True
        return False

    def get_server_config(self, name: str) -> Dict[str, Any]:
        return self.servers_config.get(name)
        
    def list_servers(self) -> Dict[str, Any]:
        return self.servers_config
