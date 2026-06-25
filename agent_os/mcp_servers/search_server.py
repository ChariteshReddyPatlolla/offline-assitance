from mcp.server.fastmcp import FastMCP
import requests
from bs4 import BeautifulSoup
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("Search")

@mcp.tool()
def search_duckduckgo(query: str, max_results: int = 5) -> str:
    """Best for general web search and privacy. Returns top links and snippets."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return json.dumps(results)
    except Exception as e:
        logger.error(f"DDG Search error: {e}")
        return json.dumps({"error": str(e)})

@mcp.tool()
def search_google(query: str, max_results: int = 5) -> str:
    """Best for broad reach and product comparisons. Returns top links."""
    try:
        from googlesearch import search
        results = list(search(query, num=max_results, stop=max_results, pause=2))
        return json.dumps([{"url": url} for url in results])
    except Exception as e:
        logger.error(f"Google Search error: {e}")
        return json.dumps({"error": str(e)})

@mcp.tool()
def search_wikipedia(query: str, sentences: int = 5) -> str:
    """Best for factual baseline context. Returns encyclopedic summary."""
    try:
        import wikipedia
        summary = wikipedia.summary(query, sentences=sentences)
        return json.dumps({"query": query, "summary": summary})
    except Exception as e:
        logger.error(f"Wikipedia error: {e}")
        return json.dumps({"error": str(e)})

@mcp.tool()
def search_arxiv(query: str, max_results: int = 3) -> str:
    """Best for academic and deeply technical papers. Returns abstracts and PDF links."""
    try:
        import arxiv
        # arxiv API syntax has changed in recent versions, client.results is preferred, but search.results() works in v2.1.0 usually
        # To be safe across versions, we use Client
        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )
        
        results = []
        for result in client.results(search):
            results.append({
                "title": result.title,
                "authors": [a.name for a in result.authors],
                "summary": result.summary,
                "pdf_url": result.pdf_url
            })
        return json.dumps(results)
    except Exception as e:
        logger.error(f"Arxiv error: {e}")
        return json.dumps({"error": str(e)})

@mcp.tool()
def fetch_page_content(url: str) -> str:
    """Fetches the raw text content of a web page, stripping HTML."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
            
        text = soup.get_text(separator=' ', strip=True)
        
        if len(text) > 15000:
            text = text[:15000] + "... [Content Truncated]"
            
        return text
    except Exception as e:
        logger.error(f"Fetch page error: {e}")
        return f"Error fetching {url}: {str(e)}"

if __name__ == "__main__":
    mcp.run()
