import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from mcp.server.fastmcp import FastMCP
from services.tools.impl.shell import execute_shell_command_raw

mcp = FastMCP("shell")

@mcp.tool()
def execute_shell_command(command: str) -> str:
    """Execute a shell command on the local machine."""
    return execute_shell_command_raw(command)

if __name__ == "__main__":
    mcp.run()
