"""
Research agent tool — autonomously researches a topic by visiting multiple web pages,
extracting content, and returning structured summaries with source links.
"""
import logging
import urllib.parse
import webbrowser
from langchain_core.tools import tool
from services.tools.browser import _open_in_chrome

logger = logging.getLogger(__name__)


@tool
def research_topic(query: str) -> str:
    """
    Autonomously researches any topic by searching multiple websites and summarizing findings.
    Returns structured results with titles, URLs, and key summaries.
    Use this when the user asks to research, find papers, learn about a topic, or gather information.
    Examples: 'research best distributed systems papers', 'find information about LangGraph',
              'research machine learning trends 2024'
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

        encoded = urllib.parse.quote(query)
        search_url = f"https://duckduckgo.com/?q={encoded}"

        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True, args=["--no-sandbox"])
            page = browser.new_page()

            # Step 1: Get search results
            logger.info("Researching topic: %s", query)
            page.goto(search_url, wait_until="domcontentloaded", timeout=15000)

            results = []
            try:
                page.wait_for_selector("[data-testid='result']", timeout=8000)
                items = page.locator("[data-testid='result']").all()[:5]
                for item in items:
                    try:
                        title = item.locator("h2").inner_text(timeout=2000)
                        url_el = item.locator("a[data-testid='result-title-a']")
                        url = url_el.get_attribute("href") or ""
                        snippet = ""
                        try:
                            snippet = item.locator("[data-result='snippet']").inner_text(timeout=1000)
                        except Exception:
                            pass
                        if url and not url.startswith("http"):
                            url = "https://" + url
                        results.append({"title": title, "url": url, "snippet": snippet, "full_text": ""})
                    except Exception:
                        pass
            except PWTimeout:
                pass

            # Step 2: Visit each result page and extract content
            for i, result in enumerate(results[:3]):
                try:
                    page2 = browser.new_page()
                    page2.goto(result["url"], wait_until="domcontentloaded", timeout=10000)
                    
                    # Extract main content text
                    content = page2.evaluate("""() => {
                        const selectors = ['article', 'main', '.content', '.post-content', '#content', 'body'];
                        for (const sel of selectors) {
                            const el = document.querySelector(sel);
                            if (el) return el.innerText.slice(0, 2000);
                        }
                        return document.body.innerText.slice(0, 2000);
                    }""")
                    result["full_text"] = content.strip()[:1500]
                    page2.close()
                except Exception as e:
                    logger.warning("Could not visit %s: %s", result["url"], e)
            
            browser.close()

            # Step 3: Format output and open links in SYSTEM browser
            if not results:
                return f"No research results found for '{query}'. Try a more specific query."

            # Open top 3 results in the user's default browser so they stay open forever
            for r in results[:3]:
                if r.get("url"):
                    try:
                        _open_in_chrome(r["url"])
                    except Exception:
                        pass

            output_parts = [f"# 🔬 Research Results: {query}\n"]
            for i, r in enumerate(results, 1):
                output_parts.append(
                    f"## {i}. {r['title']}\n"
                    f"🔗 **Source:** [{r['url']}]({r['url']})\n\n"
                    f"**Summary:** {r['snippet']}\n\n"
                    + (f"**Key Content:**\n{r['full_text'][:800]}...\n" if r['full_text'] else "")
                    + "\n---"
                )

            return "\n".join(output_parts)

    except ImportError:
        # Playwright not available — fall back to opening search
        _open_in_chrome(f"https://duckduckgo.com/?q={urllib.parse.quote(query)}")
        return (
            f"⚠️ Playwright not installed (run `playwright install chromium`). "
            f"Opened DuckDuckGo search for '{query}' in Google Chrome."
        )
    except Exception as e:
        logger.error("Research error: %s", e)
        return f"❌ Research failed: {str(e)}"
