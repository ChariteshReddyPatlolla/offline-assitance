import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from mcp.server.fastmcp import FastMCP
from services.tools.impl.desktop import (
    open_application_raw,
    close_application_raw,
    take_screenshot_description_raw,
    type_text_at_cursor_raw,
    press_hotkey_raw,
    search_start_menu_raw,
    focus_application_raw,
    minimize_application_raw,
    maximize_application_raw
)

from typing import Optional

mcp = FastMCP("automation")

@mcp.tool()
def open_application(app_name: str, path: Optional[str] = None) -> str:
    """
    Open a desktop application or program by name.
    Args:
        app_name: The application name to launch (e.g. 'notepad', 'chrome', 'vscode').
        path: Optional file or directory path to open with the application.
    """
    return open_application_raw(app_name, path)

@mcp.tool()
def close_application(app_name: str) -> str:
    """
    Closes a desktop application or specific window by its name or title.
    Args:
        app_name: The application/tab name to close (e.g. 'youtube', 'notepad').
    """
    return close_application_raw(app_name)

@mcp.tool()
def take_screenshot_description() -> str:
    """
    Describes the current screen size and cursor position state.
    """
    return take_screenshot_description_raw()

@mcp.tool()
def type_text_at_cursor(text: str) -> str:
    """
    Types the given text at the current cursor position.
    Args:
        text: The string to type.
    """
    return type_text_at_cursor_raw(text)

@mcp.tool()
def press_hotkey(keys: str) -> str:
    """
    Press a keyboard shortcut shortcut or hotkey combination.
    Args:
        keys: The hotkey string (e.g. 'ctrl+c', 'alt+tab').
    """
    return press_hotkey_raw(keys)

@mcp.tool()
def search_start_menu(query: str) -> list:
    """
    Search for applications in the Start Menu.
    Args:
        query: The application name or substring to search for.
    """
    return search_start_menu_raw(query)

@mcp.tool()
def focus_application(app_name: str) -> str:
    """
    Focus an application by bringing it to the foreground.
    Args:
        app_name: The title substring of the window to focus.
    """
    return focus_application_raw(app_name)

@mcp.tool()
def minimize_application(app_name: str) -> str:
    """
    Minimize an application window.
    Args:
        app_name: The title substring of the window to minimize.
    """
    return minimize_application_raw(app_name)

@mcp.tool()
def maximize_application(app_name: str) -> str:
    """
    Maximize an application window.
    Args:
        app_name: The title substring of the window to maximize.
    """
    return maximize_application_raw(app_name)

@mcp.tool()
def execute_workflow(steps: list) -> str:
    """
    Execute a sequence of tool calls across different MCP servers.
    Args:
        steps: A list of step dictionaries, each containing:
               - 'server': The target MCP server name (e.g. 'filesystem')
               - 'tool': The tool name to invoke (e.g. 'read_file')
               - 'arguments': A dictionary of arguments for the tool
               - 'max_retries': Optional integer. Number of times to retry on failure (default 1)
               
               Arguments can use placeholders like {{step_1}} to refer to the string output of step 1 (1-based index).
    """
    from services.mcp.client import MCPClientManager
    import time
    
    manager = MCPClientManager.get_instance()
    outputs = {}
    history = []
    
    for i, step in enumerate(steps, 1):
        server = step.get("server")
        tool_name = step.get("tool")
        args = step.get("arguments", {})
        max_retries = step.get("max_retries", 1)
        
        if not server or not tool_name:
            return f"❌ Step {i} is missing 'server' or 'tool' configuration."
            
        def interpolate(val):
            if isinstance(val, str):
                for k, v in outputs.items():
                    val = val.replace(f"{{{{{k}}}}}", str(v))
                return val
            elif isinstance(val, dict):
                return {k: interpolate(v) for k, v in val.items()}
            elif isinstance(val, list):
                return [interpolate(v) for v in val]
            return val
            
        interpolated_args = interpolate(args)
        
        attempt = 0
        success = False
        result = None
        error_msg = ""
        
        while attempt < max_retries and not success:
            attempt += 1
            try:
                result = manager.call_tool(server, tool_name, **interpolated_args)
                success = True
            except Exception as e:
                error_msg = str(e)
                if attempt < max_retries:
                    time.sleep(1)
                    
        step_key = f"step_{i}"
        outputs[step_key] = result if success else f"Error: {error_msg}"
        
        history.append({
            "step": i,
            "server": server,
            "tool": tool_name,
            "arguments": interpolated_args,
            "success": success,
            "output": outputs[step_key]
        })
        
        if not success:
            break
            
    trace = ["## ⚙️ Workflow Execution Trace\n"]
    for h in history:
        status = "✅ Succeeded" if h["success"] else "❌ Failed"
        trace.append(f"### Step {h['step']}: {h['server']}.{h['tool']} ({status})")
        trace.append(f"- **Arguments:** {h['arguments']}")
        trace.append(f"- **Output:**\n{h['output']}\n")
        
    return "\n".join(trace)

if __name__ == "__main__":
    mcp.run()
