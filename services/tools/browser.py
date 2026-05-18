"""
YouTube automation and web search tools using Playwright.
Falls back to webbrowser.open if Playwright is unavailable.
"""
import logging
import urllib.parse
import webbrowser
from langchain_core.tools import tool
import os

logger = logging.getLogger(__name__)

def _open_in_chrome(url: str):
    import subprocess
    try:
        # Force opening in Google Chrome on Windows
        subprocess.Popen(f'start chrome "{url}"', shell=True)
    except Exception:
        webbrowser.open(url)

@tool
def open_url_in_browser(url: str) -> str:
    """
    Opens a URL in the user's default web browser.
    Use this when the user asks to open a website or navigate to a URL.
    Examples: 'open youtube.com', 'go to github.com', 'open google'
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        _open_in_chrome(url)
        return f"✅ Opened '{url}' in Google Chrome."
    except Exception as e:
        return f"❌ Error opening browser: {str(e)}"

@tool
def search_youtube(query: str) -> str:
    """
    Searches YouTube for a query, opens the first video result,
    and starts playback in a persistent Chrome window.
    """
    try:
        from playwright.sync_api import sync_playwright
        import urllib.parse

        encoded = urllib.parse.quote(query)
        search_url = f"https://www.youtube.com/results?search_query={encoded}"

        video_url = None
        video_title = None

        with sync_playwright() as p:
            # Launch a temporary browser ONLY to scrape the first result.
            # This browser is headless, so closing it will not affect
            # the actual Chrome window opened later.
            browser = p.chromium.launch(
                channel="chrome",
                headless=True,
                args=["--no-sandbox"]
            )

            page = browser.new_page()
            page.goto(search_url, wait_until="domcontentloaded", timeout=20000)

            try:
                page.click("button:has-text('Accept all')", timeout=3000)
            except:
                pass

            try:
                page.click("button:has-text('Reject all')", timeout=1000)
            except:
                pass

            page.wait_for_selector("ytd-video-renderer", timeout=15000)

            first_video = page.locator(
                "ytd-video-renderer a#video-title"
            ).first

            video_title = first_video.inner_text(timeout=5000).strip()
            video_url = first_video.get_attribute("href")

            browser.close()

        if not video_url:
            return f"❌ Could not find any videos for '{query}'"

        if not video_url.startswith("http"):
            video_url = "https://www.youtube.com" + video_url

        if "?" in video_url:
            video_url += "&autoplay=1"
        else:
            video_url += "?autoplay=1"

        # IMPORTANT:
        # Open the final URL in a completely separate Chrome process.
        # This process is independent from Playwright and will stay open.
        import subprocess

        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        ]

        chrome_path = None
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_path = path
                break

        if chrome_path:
            subprocess.Popen(
                [chrome_path, video_url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False
            )
        else:
            import webbrowser
            webbrowser.open(video_url)

        return (
            f'✅ Playing "{video_title}" on YouTube.\n\n'
            f"The video has been opened in Google Chrome and will remain open."
        )

    except ImportError:
        import urllib.parse
        import webbrowser

        encoded = urllib.parse.quote(query)
        url = f"https://www.youtube.com/results?search_query={encoded}"
        webbrowser.open(url)

        return (
            "⚠️ Playwright is not installed. "
            f"Opened YouTube search for '{query}' in your browser."
        )

    except Exception as e:
        try:
            import urllib.parse
            import webbrowser

            encoded = urllib.parse.quote(query)
            url = f"https://www.youtube.com/results?search_query={encoded}"
            webbrowser.open(url)

            return (
                f"⚠️ Auto-play failed: {e}\n"
                f"Opened YouTube search for '{query}' in your browser."
            )
        except Exception as fallback_error:
            return f"❌ Error opening YouTube: {fallback_error}"
@tool
def web_search(query: str) -> str:
    """
    Search the web for current and general information using DuckDuckGo.

    Use this tool whenever the user asks for:
    - Weather
    - News
    - Current events
    - Stock prices
    - Company information
    - Definitions
    - Tutorials
    - Facts that may be recent or changing over time

    This tool returns summarized search results including titles, URLs,
    and snippets so the assistant can answer directly instead of asking
    the user to search manually.
    """
    import urllib.parse

    try:
        from playwright.sync_api import sync_playwright

        # Check if the query is a request for latest/current news or updates
        is_news_request = any(
            term in query.lower()
            for term in ["news", "latest", "recent", "current", "update", "today", "now", "happening"]
        )

        # Append current year (2026) to search query for news requests if not already present
        search_query = query
        if is_news_request and "2026" not in query:
            search_query = f"{query} 2026"

        encoded = urllib.parse.quote(search_query)
        
        # Build search URL. For news requests, restrict to the past month (df=m) to prioritize up-to-date news!
        search_url = f"https://html.duckduckgo.com/html/?q={encoded}"
        if is_news_request:
            search_url += "&df=m"

        with sync_playwright() as p:
            browser = p.chromium.launch(
                channel="chrome",
                headless=True,
                args=["--no-sandbox"],
            )

            # Use a realistic User-Agent to bypass bot detection blocks completely
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                }
            )
            page = context.new_page()

            # Use HTML-only DuckDuckGo endpoint for more reliable scraping
            page.goto(
                search_url,
                wait_until="domcontentloaded",
                timeout=20000,
            )

            results = []

            # HTML DuckDuckGo uses .result containers
            page.wait_for_selector(".result", timeout=10000)

            items = page.locator(".result").all()[:5]

            for item in items:
                try:
                    # Title
                    title = ""
                    try:
                        title = item.locator(".result__title").inner_text(timeout=2000).strip()
                    except Exception:
                        pass

                    # URL
                    url = ""
                    try:
                        url = (
                            item.locator(".result__url")
                            .inner_text(timeout=2000)
                            .strip()
                        )
                    except Exception:
                        try:
                            url = (
                                item.locator(".result__a")
                                .get_attribute("href")
                                or ""
                            )
                        except Exception:
                            pass

                    # Clean the URL and extract the domain for favicon logo
                    cleaned_url = url
                    domain = ""
                    if url:
                        if "uddg=" in url:
                            parsed_url = urllib.parse.urlparse(url)
                            queries = urllib.parse.parse_qs(parsed_url.query)
                            if "uddg" in queries:
                                cleaned_url = queries["uddg"][0]

                        if cleaned_url.startswith("//"):
                            cleaned_url = "https:" + cleaned_url
                        elif not cleaned_url.startswith("http"):
                            cleaned_url = "https://" + cleaned_url

                        try:
                            domain = urllib.parse.urlparse(cleaned_url).netloc
                            if domain.startswith("www."):
                                domain = domain[4:]
                        except Exception:
                            pass

                    # Snippet
                    snippet = ""
                    try:
                        snippet = (
                            item.locator(".result__snippet")
                            .inner_text(timeout=2000)
                            .strip()
                        )
                    except Exception:
                        pass

                    if title or snippet:
                        block = []

                        if title:
                            block.append(f"Title: {title}")

                        if cleaned_url:
                            block.append(f"URL: {cleaned_url}")

                        if domain:
                            block.append(f"Domain: {domain}")
                            logo_url = f"https://www.google.com/s2/favicons?sz=16&domain={domain}"
                            block.append(f"Logo: {logo_url}")
                            block.append(f"MarkdownLink: ![logo]({logo_url}) [{title or domain}]({cleaned_url})")

                        if snippet:
                            block.append(f"Snippet: {snippet}")

                        results.append("\n".join(block))

                except Exception:
                    continue

            browser.close()

        if results:
            return (
                f"Search results for: {query}\n\n"
                + "\n\n---\n\n".join(results)
            )

        return f"No relevant search results found for '{query}'."

    except ImportError:
        # Playwright not installed
        return (
            "Web search failed because Playwright is not installed. "
            "Install it using:\n"
            "pip install playwright\n"
            "playwright install"
        )

    except Exception as e:
        return f"Error performing web search: {str(e)}"