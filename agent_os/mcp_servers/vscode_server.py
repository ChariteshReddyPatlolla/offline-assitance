from mcp.server.fastmcp import FastMCP
import subprocess

mcp = FastMCP("VSCode")

@mcp.tool()
def open_in_vscode(path: str) -> str:
    """Opens a file or directory in VSCode."""
    subprocess.run(["code", path], shell=True)
    return f"Opened {path} in VSCode."

@mcp.tool()
def install_extension(extension_id: str) -> str:
    """Installs a VSCode extension."""
    subprocess.run(["code", "--install-extension", extension_id], shell=True)
    return f"Installed {extension_id}"

@mcp.tool()
def run_code_in_vscode_terminal(command: str) -> str:
    """
    Focus VS Code, open the integrated terminal, and execute a command.
    """
    import pyautogui
    import time
    
    # Switch to VSCode
    subprocess.run(["code"], shell=True)
    time.sleep(1.0)
    
    # Toggle terminal (Ctrl + `)
    pyautogui.hotkey('ctrl', '`')
    time.sleep(0.5)
    
    # Type command and press enter
    pyautogui.typewrite(command + "\n", interval=0.03)
    return f"Executed command in VSCode terminal: {command}"

if __name__ == "__main__":
    mcp.run()
