from mcp.server.fastmcp import FastMCP
import subprocess

mcp = FastMCP("Git")

@mcp.tool()
def git_status() -> str:
    """Returns the current git status."""
    result = subprocess.run(["git", "status"], capture_output=True, text=True)
    return result.stdout

@mcp.tool()
def git_commit(message: str) -> str:
    """Commits all staged changes."""
    result = subprocess.run(["git", "commit", "-m", message], capture_output=True, text=True)
    return result.stdout

if __name__ == "__main__":
    mcp.run()
