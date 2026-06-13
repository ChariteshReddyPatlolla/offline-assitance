import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from mcp.server.fastmcp import FastMCP
from services.tools.impl.email import draft_email_raw

mcp = FastMCP("email")

@mcp.tool()
def draft_email(to: str, subject: str, body: str) -> str:
    """Draft and send an email automatically via SMTP."""
    return draft_email_raw(to, subject, body)

if __name__ == "__main__":
    mcp.run()
