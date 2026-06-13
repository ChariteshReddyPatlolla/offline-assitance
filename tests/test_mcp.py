import pytest
import os
import json
import asyncio
from agent_os.mcp.registry import MCPRegistry

@pytest.mark.asyncio
async def test_mcp_registry_hot_loading():
    config_path = "test_mcp_config.json"
    
    # Create initial config
    with open(config_path, "w") as f:
        json.dump({"mcpServers": {}}, f)
        
    registry = MCPRegistry(config_path)
    
    # First load
    changed = await registry.load_config()
    assert changed is True
    assert registry.list_servers() == {}
    
    # Wait to ensure mtime changes
    await asyncio.sleep(0.1)
    
    # Second load (no change)
    changed = await registry.load_config()
    assert changed is False
    
    # Wait to ensure mtime changes
    await asyncio.sleep(0.1)
    
    # Modify config
    with open(config_path, "w") as f:
        json.dump({"mcpServers": {"test": {}}}, f)
        
    # Third load (changed)
    changed = await registry.load_config()
    assert changed is True
    assert "test" in registry.list_servers()
    
    # Clean up
    os.remove(config_path)
