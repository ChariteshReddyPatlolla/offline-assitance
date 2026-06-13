from mcp.server.fastmcp import FastMCP
import subprocess

mcp = FastMCP("Shell")

@mcp.tool()
def execute_command(command: str) -> str:
    """Executes a shell command and returns the output."""
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True
    )
    if result.returncode == 0:
        return result.stdout
    else:
        return f"Error: {result.stderr}"

if __name__ == "__main__":
    mcp.run()
