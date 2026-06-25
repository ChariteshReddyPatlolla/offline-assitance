from mcp.server.fastmcp import FastMCP
import os

mcp = FastMCP("Filesystem")

@mcp.tool()
def read_file(path: str) -> str:
    """Reads the contents of a file."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

@mcp.tool()
def write_file(path: str, content: str) -> str:
    """Writes content to a file."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Successfully wrote to {path}"

if __name__ == "__main__":
    mcp.run()
