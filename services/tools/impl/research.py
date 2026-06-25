import logging
import urllib.parse
import os

logger = logging.getLogger(__name__)

def research_topic_raw(query: str) -> str:
    """Autonomously researches any topic by searching multiple websites and summarizing findings.
    
    Uses the HTML DuckDuckGo endpoint (reliable, no JS required) to fetch real search results,
    then visits the top pages to extract actual content. Returns real URLs and real content only.
    """
    import concurrent.futures
    with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_research_topic_sync_worker, query)
        return future.result()

def _research_topic_sync_worker(query: str) -> str:
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
        from services.tools.impl.browser import get_brave_path, web_search_raw

        encoded = urllib.parse.quote(query)
        search_url = f"https://html.duckduckgo.com/html/?q={encoded}"

        with sync_playwright() as p:
            brave_path = get_brave_path()
            try:
                if brave_path:
                    browser = p.chromium.launch(executable_path=brave_path, headless=True, args=["--no-sandbox"])
                else:
                    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            except Exception:
                browser = p.chromium.launch(headless=True, args=["--no-sandbox"])

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            )
            page = context.new_page()

            logger.info("Researching topic: %s", query)
            page.goto(search_url, wait_until="domcontentloaded", timeout=20000)

            results = []
            try:
                page.wait_for_selector(".result", timeout=10000)
                items = page.locator(".result").all()[:6]
                for item in items:
                    try:
                        title = ""
                        try:
                            title = item.locator(".result__title").inner_text(timeout=2000).strip()
                        except Exception:
                            pass

                        raw_url = ""
                        try:
                            raw_url = item.locator(".result__url").inner_text(timeout=2000).strip()
                        except Exception:
                            try:
                                raw_url = item.locator(".result__a").get_attribute("href") or ""
                            except Exception:
                                pass

                        # Clean DuckDuckGo redirect URLs
                        cleaned_url = raw_url
                        if "uddg=" in raw_url:
                            parsed = urllib.parse.urlparse(raw_url)
                            qs = urllib.parse.parse_qs(parsed.query)
                            if "uddg" in qs:
                                cleaned_url = qs["uddg"][0]
                        if cleaned_url.startswith("//"):
                            cleaned_url = "https:" + cleaned_url
                        elif cleaned_url and not cleaned_url.startswith("http"):
                            cleaned_url = "https://" + cleaned_url

                        snippet = ""
                        try:
                            snippet = item.locator(".result__snippet").inner_text(timeout=2000).strip()
                        except Exception:
                            pass

                        if title and cleaned_url and cleaned_url.startswith("http"):
                            results.append({"title": title, "url": cleaned_url, "snippet": snippet, "full_text": ""})
                    except Exception:
                        pass
            except PWTimeout:
                logger.warning("Timed out waiting for DuckDuckGo results for query: %s", query)

            # Visit up to 3 pages and extract actual content
            for result in results[:3]:
                try:
                    page2 = context.new_page()
                    page2.goto(result["url"], wait_until="domcontentloaded", timeout=12000)
                    content = page2.evaluate("""() => {
                        const selectors = ['article', 'main', '.content', '.post-content', '#content', '.article-body', '.entry-content', 'body'];
                        for (const sel of selectors) {
                            const el = document.querySelector(sel);
                            if (el) {
                                const text = el.innerText.replace(/\\s+/g, ' ').trim();
                                if (text.length > 100) return text.slice(0, 2500);
                            }
                        }
                        return document.body.innerText.replace(/\\s+/g, ' ').trim().slice(0, 2500);
                    }""")
                    result["full_text"] = content.strip()[:1800]
                    page2.close()
                except Exception as e:
                    logger.warning("Could not visit %s: %s", result["url"], e)

            browser.close()

        if not results:
            return (
                f"No research results found for '{query}'. "
                f"The search returned no pages. Try a more specific query or use web_search instead."
            )

        # Build rich output with real URLs and real content
        output_parts = [f"# 🔬 Research Results: {query}\n"]
        for i, r in enumerate(results, 1):
            domain = ""
            try:
                domain = urllib.parse.urlparse(r["url"]).netloc.lstrip("www.")
            except Exception:
                pass

            logo_md = f"![logo](https://www.google.com/s2/favicons?sz=16&domain={domain}) " if domain else ""
            content_block = (
                f"\n**Key Content:**\n{r['full_text'][:1000]}...\n" if r["full_text"] else ""
            )
            output_parts.append(
                f"## {i}. {r['title']}\n"
                f"🔗 **Source:** {logo_md}[{r['url']}]({r['url']})\n\n"
                f"**Summary:** {r['snippet']}\n"
                + content_block
                + "\n---"
            )

        return "\n".join(output_parts)

    except ImportError:
        import webbrowser
        webbrowser.open(f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}")
        return (
            f"⚠️ Playwright not installed (run `playwright install chromium`). "
            f"Opened DuckDuckGo search for '{query}' in Chrome."
        )
    except Exception as e:
        logger.error("Research error: %s", e)
        return f"❌ Research failed: {str(e)}"

def scrape_page_raw(url: str) -> str:
    """Navigate to a URL and extract its main text content using Playwright."""
    import concurrent.futures
    with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_scrape_page_sync_worker, url)
        return future.result()

def _scrape_page_sync_worker(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        from playwright.sync_api import sync_playwright
        from services.tools.impl.browser import get_brave_path
        
        brave_path = get_brave_path()
        with sync_playwright() as p:
            try:
                if brave_path:
                    browser = p.chromium.launch(executable_path=brave_path, headless=True, args=["--no-sandbox"])
                else:
                    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            except Exception:
                browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
                
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            
            content = page.evaluate("""() => {
                const selectors = ['article', 'main', '.content', '.post-content', '#content', '.article-body', 'body'];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el) {
                        const text = el.innerText.replace(/\\s+/g, ' ').trim();
                        if (text.length > 200) return text;
                    }
                }
                return document.body.innerText.replace(/\\s+/g, ' ').trim();
            }""")
            
            browser.close()
            
        if not content:
            return "No content could be extracted from the page."
            
        if len(content) > 8000:
            return content[:8000] + "\n\n[... Page content truncated ...]"
        return content
    except Exception as e:
        return f"❌ Failed to scrape page: {str(e)}"

def extract_links_raw(url: str) -> str:
    """Navigate to a URL and extract all links on it."""
    import concurrent.futures
    with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_extract_links_sync_worker, url)
        return future.result()

def _extract_links_sync_worker(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        from playwright.sync_api import sync_playwright
        from services.tools.impl.browser import get_brave_path
        
        brave_path = get_brave_path()
        with sync_playwright() as p:
            try:
                if brave_path:
                    browser = p.chromium.launch(executable_path=brave_path, headless=True, args=["--no-sandbox"])
                else:
                    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            except Exception:
                browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
                
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            
            links = page.evaluate("""() => {
                const anchors = Array.from(document.querySelectorAll('a'));
                return anchors.map(a => ({
                    text: a.innerText.trim(),
                    href: a.href
                })).filter(a => a.href && a.href.startsWith('http'));
            }""")
            
            browser.close()
            
        if not links:
            return "No links found on the page."
            
        seen = set()
        unique_links = []
        for link in links:
            href = link["href"]
            if href not in seen:
                seen.add(href)
                unique_links.append(link)
                
        output = [f"Found {len(unique_links)} links (showing first 100):"]
        for i, link in enumerate(unique_links[:100], 1):
            text_desc = f" ({link['text']})" if link["text"] else ""
            output.append(f"{i}. [{link['href']}]({link['href']}){text_desc}")
            
        return "\n".join(output)
    except Exception as e:
        return f"❌ Failed to extract links: {str(e)}"
