from langchain_core.tools import tool
from services.mcp.client import MCPClientManager

from typing import Optional

@tool
def open_application(app_name: str, path: Optional[str] = None) -> str:
    """
    Open a desktop application or program by name.
    """
    return MCPClientManager.get_instance().call_tool(
        "automation", "open_application", app_name=app_name, path=path
    )

@tool
def close_application(app_name: str) -> str:
    """
    Closes a desktop application or specific window by its name or title.
    """
    return MCPClientManager.get_instance().call_tool(
        "automation", "close_application", app_name=app_name
    )

@tool
def take_screenshot_description() -> str:
    """
    Describes the current screen state. Returns a summary of what's visible.
    """
    return MCPClientManager.get_instance().call_tool(
        "automation", "take_screenshot_description"
    )

@tool
def type_text_at_cursor(text: str) -> str:
    """
    Types the given text at the current cursor position using keyboard simulation.
    """
    return MCPClientManager.get_instance().call_tool(
        "automation", "type_text_at_cursor", text=text
    )

@tool
def press_hotkey(keys: str) -> str:
    """
    Press a keyboard shortcut or hotkey combination.
    """
    return MCPClientManager.get_instance().call_tool(
        "automation", "press_hotkey", keys=keys
    )

@tool
def search_start_menu(query: str) -> list:
    """
    Search for applications in the Start Menu.
    """
    return MCPClientManager.get_instance().call_tool(
        "automation", "search_start_menu", query=query
    )

@tool
def focus_application(app_name: str) -> str:
    """
    Focus an application by bringing it to the foreground.
    """
    return MCPClientManager.get_instance().call_tool(
        "automation", "focus_application", app_name=app_name
    )

@tool
def minimize_application(app_name: str) -> str:
    """
    Minimize an application window.
    """
    return MCPClientManager.get_instance().call_tool(
        "automation", "minimize_application", app_name=app_name
    )

@tool
def maximize_application(app_name: str) -> str:
    """
    Maximize an application window.
    """
    return MCPClientManager.get_instance().call_tool(
        "automation", "maximize_application", app_name=app_name
    )

@tool
def run_editor_sync_demo() -> str:
    """
    Natively automates the complete visual VS Code and Notepad editor synchronization demo.
    """
    return MCPClientManager.get_instance().call_tool(
        "vscode", "run_editor_sync_demo"
    )

@tool
def open_file_in_vscode(filepath: str) -> str:
    """
    Open a file in the VS Code desktop app.
    """
    from shared.context import active_session_dir
    import os
    user_profile = os.environ.get("USERPROFILE", r"C:\Users\patlo")
    desktop = os.path.join(user_profile, "Desktop")
    onedrive_desktop = os.path.join(user_profile, "OneDrive", "Desktop")
    if os.path.exists(onedrive_desktop):
        desktop = onedrive_desktop
        
    current_dir = active_session_dir.get() or desktop
    if not os.path.isabs(filepath):
        filepath = os.path.join(current_dir, filepath)
    abs_path = os.path.abspath(filepath)
    return MCPClientManager.get_instance().call_tool(
        "vscode", "open_file_in_vscode", filepath=abs_path
    )

@tool
def open_folder_in_vscode(folderpath: str) -> str:
    """
    Open a folder in the VS Code desktop app.
    """
    from shared.context import active_session_dir
    import os
    user_profile = os.environ.get("USERPROFILE", r"C:\Users\patlo")
    desktop = os.path.join(user_profile, "Desktop")
    onedrive_desktop = os.path.join(user_profile, "OneDrive", "Desktop")
    if os.path.exists(onedrive_desktop):
        desktop = onedrive_desktop
        
    current_dir = active_session_dir.get() or desktop
    if not os.path.isabs(folderpath):
        folderpath = os.path.join(current_dir, folderpath)
    abs_path = os.path.abspath(folderpath)
    return MCPClientManager.get_instance().call_tool(
        "vscode", "open_folder_in_vscode", folderpath=abs_path
    )

@tool
def run_command_in_vscode_terminal(command: str) -> str:
    """
    Focus VS Code, open the integrated terminal, and execute a command.
    """
    return MCPClientManager.get_instance().call_tool(
        "vscode", "run_command_in_vscode_terminal", command=command
    )

@tool
def execute_workflow(steps: list) -> str:
    """
    Execute a sequence of tool calls across different MCP servers.
    """
    return MCPClientManager.get_instance().call_tool(
        "automation", "execute_workflow", steps=steps
    )
