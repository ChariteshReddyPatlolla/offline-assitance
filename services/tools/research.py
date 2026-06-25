from langchain_core.tools import tool
from services.mcp.client import MCPClientManager

@tool
def research_topic(query: str) -> str:
    """
    Autonomously researches any topic by searching multiple websites and summarizing findings.
    """
    return MCPClientManager.get_instance().call_tool(
        "research", "research_topic", query=query
    )

@tool
def scrape_page(url: str) -> str:
    """
    Navigate to a URL and extract its main text content using Playwright.
    """
    return MCPClientManager.get_instance().call_tool(
        "research", "scrape_page", url=url
    )

@tool
def extract_links(url: str) -> str:
    """
    Navigate to a URL and extract all links on it.
    """
    return MCPClientManager.get_instance().call_tool(
        "research", "extract_links", url=url
    )

@tool
def search_jobs(query: str) -> str:
    """
    Searches for current job postings using a reliable remote jobs API (Remotive).
    Returns a formatted list of jobs matching the query.
    """
    import urllib.request
    import urllib.parse
    import json
    try:
        url = f"https://remotive.com/api/remote-jobs?search={urllib.parse.quote(query)}&limit=15"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
        
        jobs = data.get('jobs', [])[:10]
        if not jobs:
            return f"No jobs found for '{query}' on Remotive API."
            
        result = [f"Found {len(jobs)} jobs for '{query}':"]
        for j in jobs:
            result.append(f"- Title: {j.get('title')}\n  Company: {j.get('company_name')}\n  URL: {j.get('url')}\n  Type: {j.get('job_type')}")
            
        return "\n\n".join(result)
    except Exception as e:
        return f"Error searching for jobs: {str(e)}"
