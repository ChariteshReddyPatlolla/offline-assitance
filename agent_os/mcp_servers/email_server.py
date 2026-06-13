from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Email")

@mcp.tool()
def send_email(to: str, subject: str, body: str) -> str:
    """Sends an email. (Stubbed)"""
    return f"Sent email to {to} with subject: {subject}"

@mcp.tool()
def read_inbox(limit: int = 5) -> str:
    """Reads the recent emails from inbox. (Stubbed)"""
    return f"Returned {limit} recent emails."

if __name__ == "__main__":
    mcp.run()
