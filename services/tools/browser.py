"""
YouTube automation and web search tools using Playwright.
Provides a persistent, headed browser manager that reuses the same tab/window for subsequent searches.
"""
import logging
import urllib.parse
import webbrowser
from langchain_core.tools import tool
import os

logger = logging.getLogger(__name__)


def get_brave_path() -> str:
    """Helper to locate the Brave Browser executable on Windows."""
    paths = [
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Users\patlo\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe",
    ]
    # General fallback using environment variables
    userprofile = os.environ.get("USERPROFILE", "C:\\Users\\patlo")
    paths.append(os.path.join(userprofile, r"AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"))
    
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def _open_in_chrome(url: str):
    """Helper to open a URL in Brave on Windows, with fallback to default browser."""
    brave_path = get_brave_path()
    if brave_path:
        import subprocess
        try:
            # Open Brave browser with url directly
            subprocess.Popen(f'"{brave_path}" "{url}"', shell=True)
            return
        except Exception:
            pass
            
    # Try calling system command 'brave'
    import subprocess
    try:
        subprocess.Popen(f'start brave "{url}"', shell=True)
    except Exception:
        webbrowser.open(url)


def close_persistent_browser() -> bool:
    """
    Closes the active persistent Playwright browser page and browser instance gracefully.
    Returns True if a persistent session was active and closed, False otherwise.
    """
    global _active_browser, _active_page, _playwright_context
    success = False
    try:
        if _active_page is not None:
            _active_page.close()
            _active_page = None
            success = True
    except Exception as e:
        logger.warning("Error closing persistent page: %s", str(e))
        
    try:
        if _active_browser is not None:
            _active_browser.close()
            _active_browser = None
            success = True
    except Exception as e:
        logger.warning("Error closing persistent browser: %s", str(e))
        
    try:
        if _playwright_context is not None:
            _playwright_context.stop()
            _playwright_context = None
    except:
        pass
        
    return success


# -----------------------------------------------------------------------------
# Persistent Playwright browser session variables
# Allows the AI assistant to reuse the exact same browser tab/window!
# -----------------------------------------------------------------------------
_playwright_context = None
_active_browser = None
_active_page = None


def _initialize_browser_if_needed():
    """Initializes the Playwright context and headed browser if they are not already running."""
    global _playwright_context, _active_browser
    
    from playwright.sync_api import sync_playwright
    if _playwright_context is None:
        try:
            _playwright_context = sync_playwright().start()
        except Exception as e:
            logger.error("Failed to start Playwright: %s", str(e))
            raise e
            
    if _active_browser is None:
        brave_path = get_brave_path()
        try:
            if brave_path:
                _active_browser = _playwright_context.chromium.launch(
                    executable_path=brave_path,  # Controls Brave Browser directly!
                    headless=False,
                    args=["--no-sandbox", "--start-maximized"]
                )
            else:
                # Fallback to Microsoft Edge if Brave is not found
                _active_browser = _playwright_context.chromium.launch(
                    channel="msedge",
                    headless=False,
                    args=["--no-sandbox", "--start-maximized"]
                )
        except Exception as e:
            logger.warning("Failed to launch Brave/Edge, falling back to standard Chromium: %s", str(e))
            # Fallback to standard Chromium if Edge/Brave fails
            try:
                _active_browser = _playwright_context.chromium.launch(
                    headless=False,
                    args=["--no-sandbox", "--start-maximized"]
                )
            except Exception as e_inner:
                logger.error("Failed to launch standard Chromium: %s", str(e_inner))
                raise e_inner


def get_active_page():
    """
    Returns the active Playwright headed page or initializes a new headed browser session
    if it is not running. Automatically heals if the browser window is closed.
    """
    global _active_browser, _active_page
    
    # 1. Check if browser and page are still active and open
    if _active_browser is not None:
        try:
            if _active_page is not None and not _active_page.is_closed():
                # Focus the browser window and bring it to the front
                try:
                    _active_page.bring_to_front()
                except:
                    pass
                return _active_page
        except Exception:
            pass
            
        # If the page was closed but browser is alive, spawn a new tab
        try:
            _active_page = _active_browser.new_page()
            return _active_page
        except Exception:
            # If that fails, close and reset browser variables
            try:
                _active_browser.close()
            except:
                pass
            _active_browser = None
            
    # 2. Initialize a fresh Playwright headed Brave/Edge/Chromium session
    _initialize_browser_if_needed()
    try:
        _active_page = _active_browser.new_page()
        return _active_page
    except Exception as e:
        logger.error("Failed to create new page: %s", str(e))
        raise e


def get_or_create_page(target_url: str):
    """
    Returns an active Playwright page. If a page with a matching domain is already open,
    brings it to the front and navigates it to target_url if the exact URLs differ.
    Otherwise, creates a new page and navigates it.
    """
    global _active_browser, _active_page
    
    # 1. Initialize browser if needed
    _initialize_browser_if_needed()
    
    if not target_url.startswith(("http://", "https://")):
        target_url = "https://" + target_url

    # 2. Extract domain from target URL
    parsed_target = urllib.parse.urlparse(target_url)
    target_domain = parsed_target.netloc.lower().replace("www.", "")
    if not target_domain and parsed_target.path:
        target_domain = parsed_target.path.lower()
        
    def is_matching(page_url: str) -> bool:
        if not page_url:
            return False
        parsed_page = urllib.parse.urlparse(page_url)
        page_domain = parsed_page.netloc.lower().replace("www.", "")
        return target_domain in page_domain or target_domain in page_url.lower()

    # 3. Check if _active_page exists and is open
    if _active_page is not None:
        try:
            if not _active_page.is_closed():
                if is_matching(_active_page.url):
                    _active_page.bring_to_front()
                    if _active_page.url.rstrip("/") != target_url.rstrip("/"):
                        _active_page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                    return _active_page
        except Exception:
            _active_page = None

    # 4. Search all open pages in all active browser contexts
    if _active_browser is not None:
        try:
            for context in _active_browser.contexts:
                for page in context.pages:
                    if not page.is_closed() and is_matching(page.url):
                        _active_page = page
                        page.bring_to_front()
                        if page.url.rstrip("/") != target_url.rstrip("/"):
                            page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                        return page
        except Exception:
            pass

    # 5. If _active_page exists and is open but not matching, reuse it to navigate
    if _active_page is not None:
        try:
            if not _active_page.is_closed():
                _active_page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                _active_page.bring_to_front()
                return _active_page
        except Exception:
            _active_page = None

    # 6. Otherwise create a new page/tab and navigate
    try:
        context = _active_browser.contexts[0] if _active_browser.contexts else _active_browser.new_context()
        _active_page = context.new_page()
        _active_page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
        _active_page.bring_to_front()
        return _active_page
    except Exception as e:
        logger.exception("Failed to open page")
        raise e


@tool
def open_url_in_browser(url: str) -> str:
    """
    Opens a URL in the user's persistent, active desktop browser.
    Use this when the user asks to open a website or navigate to a URL.
    Examples: 'open youtube.com', 'go to github.com', 'open google'
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
        
    try:
        page = get_or_create_page(url)
        return f"✅ Navigated to '{url}' in your active browser window."
    except Exception as e:
        logger.warning("Playwright persistent browser failed, falling back to default system browser: %s", str(e))
        # Complete fallback to standard system browser
        try:
            webbrowser.open(url)
            return f"✅ Opened '{url}' in your default system web browser."
        except Exception as e_fallback:
            return f"❌ Error opening browser: {str(e_fallback)}"


@tool
def search_youtube(query: str) -> str:
    """
    Searches YouTube for a song or video query, and plays the first video result
    directly inside your active persistent browser tab.
    Use this when the user asks to "play a song", "search songs", or "play video on youtube".
    """
    encoded = urllib.parse.quote(query)
    search_url = f"https://www.youtube.com/results?search_query={encoded}"
    
    try:
        page = get_or_create_page("https://www.youtube.com")
        
        # If we are already on YouTube, try to use the search bar first
        if "youtube.com" in page.url:
            try:
                # Find search box, clear it, type query and press Enter
                search_input = page.locator("input#search, input[name='search_query']").first
                search_input.click()
                search_input.fill("")
                search_input.fill(query)
                search_input.press("Enter")
                # Wait briefly for results page
                page.wait_for_selector("ytd-video-renderer", timeout=10000)
            except Exception:
                # Fallback to direct navigation
                page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        else:
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        
        # Handle YouTube cookie prompts if they block the page
        try:
            page.click("button:has-text('Accept all')", timeout=1500)
        except:
            pass
            
        try:
            page.click("button:has-text('Reject all')", timeout=1000)
        except:
            pass
            
        # Wait for YouTube's video renderer list to appear
        page.wait_for_selector("ytd-video-renderer", timeout=15000)
        
        # Click the first video title link to load and play it in the same window!
        first_video = page.locator("ytd-video-renderer a#video-title").first
        video_title = first_video.inner_text(timeout=5000).strip()
        
        # Navigate to the video page
        first_video.click()
        
        return f"✅ Playing '{video_title}' on YouTube in your persistent browser window."
        
    except Exception as e:
        logger.warning("Playwright search_youtube failed, falling back to system browser: %s", str(e))
        # Fallback to opening search results in system default browser
        try:
            encoded_fallback = urllib.parse.quote(query)
            url_fallback = f"https://www.youtube.com/results?search_query={encoded_fallback}"
            webbrowser.open(url_fallback)
            return f"⚠️ Opened YouTube search for '{query}' in your system browser."
        except Exception as e_fallback:
            return f"❌ Error opening YouTube: {str(e_fallback)}"


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

        brave_path = get_brave_path()
        with sync_playwright() as p:
            try:
                if brave_path:
                    browser = p.chromium.launch(
                        executable_path=brave_path,
                        headless=True,
                        args=["--no-sandbox"],
                    )
                else:
                    browser = p.chromium.launch(
                        headless=True,
                        args=["--no-sandbox"],
                    )
            except Exception:
                browser = p.chromium.launch(
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


@tool
def pause_playback() -> str:
    """
    Pauses video or audio playback on the active YouTube or browser tab.
    Use this when the user asks to "pause", "stop playing", "stop music", or "pause video".
    """
    global _active_page
    if _active_page is not None:
        try:
            if not _active_page.is_closed():
                _active_page.bring_to_front()
                _active_page.evaluate("document.querySelectorAll('video').forEach(v => v.pause())")
                return "✅ Stopped playing (paused video playback on the active browser tab)."
        except Exception as e:
            return f"❌ Failed to pause video: {str(e)}"
    return "ℹ️ No active browser tab was open to pause."