import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from mcp.server.fastmcp import FastMCP
from services.tools.impl.research import (
    research_topic_raw,
    scrape_page_raw,
    extract_links_raw
)
from services.tools.impl.browser import web_search_raw

mcp = FastMCP("research")

@mcp.tool()
def research_topic(query: str) -> str:
    """Autonomously researches any topic by searching multiple websites and summarizing findings."""
    return research_topic_raw(query)

@mcp.tool()
def web_search(query: str) -> str:
    """Search the web for information using DuckDuckGo."""
    return web_search_raw(query)

@mcp.tool()
def scrape_page(url: str) -> str:
    """Navigate to a URL and extract its main text content using Playwright."""
    return scrape_page_raw(url)

@mcp.tool()
def extract_links(url: str) -> str:
    """Navigate to a URL and extract all links on it."""
    return extract_links_raw(url)

if __name__ == "__main__":
    mcp.run()
