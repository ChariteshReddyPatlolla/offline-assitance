import logging
import urllib.parse
import webbrowser
import os

import concurrent.futures

logger = logging.getLogger(__name__)

# State variables for the persistent browser session
_playwright_context = None
_active_browser = None
_active_page = None

# Create a dedicated, single background thread for ALL Playwright operations.
# Playwright's sync_api strictly requires that the context and browser be
# interacted with on the exact same thread they were created on, AND that
# thread must NOT have a running asyncio event loop.
_playwright_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="PlaywrightWorker")

def run_in_playwright_thread(func, *args, **kwargs):
    """Executes a function in the dedicated Playwright thread and waits for the result."""
    future = _playwright_executor.submit(func, *args, **kwargs)
    return future.result()

def get_brave_path() -> str:
    """Helper to locate the Brave Browser executable on Windows."""
    paths = [
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Users\patlo\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe",
    ]
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
            subprocess.Popen(f'"{brave_path}" "{url}"', stdin=subprocess.DEVNULL, shell=True)
            return
        except Exception:
            pass
            
    import subprocess
    try:
        subprocess.Popen(f'start brave "{url}"', stdin=subprocess.DEVNULL, shell=True)
    except Exception:
        webbrowser.open(url)

def _close_persistent_browser_sync() -> bool:
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

def close_persistent_browser() -> bool:
    """Closes the active persistent Playwright browser page and browser instance gracefully."""
    return run_in_playwright_thread(_close_persistent_browser_sync)

def _initialize_browser_sync():
    """Initializes the Playwright context and headed browser (runs in dedicated thread)."""
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
                    executable_path=brave_path,
                    headless=False,
                    args=["--no-sandbox", "--start-maximized"]
                )
            else:
                _active_browser = _playwright_context.chromium.launch(
                    channel="msedge",
                    headless=False,
                    args=["--no-sandbox", "--start-maximized"]
                )
        except Exception as e:
            logger.warning("Failed to launch Brave/Edge, falling back to standard Chromium: %s", str(e))
            try:
                _active_browser = _playwright_context.chromium.launch(
                    headless=False,
                    args=["--no-sandbox", "--start-maximized"]
                )
            except Exception as e_inner:
                logger.error("Failed to launch standard Chromium: %s", str(e_inner))
                raise e_inner

def _initialize_browser_if_needed():
    run_in_playwright_thread(_initialize_browser_sync)

def _get_active_page_sync():
    global _active_browser, _active_page
    
    if _active_browser is not None:
        try:
            if _active_page is not None and not _active_page.is_closed():
                try:
                    _active_page.bring_to_front()
                except:
                    pass
                return _active_page
        except Exception:
            pass
            
        try:
            _active_page = _active_browser.new_page()
            return _active_page
        except Exception:
            try:
                _active_browser.close()
            except:
                pass
            _active_browser = None
            
    _initialize_browser_sync()
    try:
        _active_page = _active_browser.new_page()
        return _active_page
    except Exception as e:
        logger.error("Failed to create new page: %s", str(e))
        raise e

def get_active_page():
    """Returns the active Playwright headed page or initializes a new headed browser session."""
    return run_in_playwright_thread(_get_active_page_sync)

def focus_browser_window():
    global _active_page
    if _active_page is not None:
        try:
            title = _active_page.title()
            if title:
                import subprocess
                cmd = f"powershell -Command \"$ws = New-Object -ComObject wscript.shell; [void]$ws.AppActivate('{title}')\""
                subprocess.run(cmd, stdin=subprocess.DEVNULL, shell=True, capture_output=True)
        except Exception:
            pass

def get_or_create_page(target_url: str):
    """Returns page. Matches and brings domain tab to front if already open."""
    global _active_browser, _active_page
    
    _initialize_browser_if_needed()
    
    if not target_url.startswith(("http://", "https://")):
        target_url = "https://" + target_url

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

    if _active_page is not None:
        try:
            if not _active_page.is_closed():
                if is_matching(_active_page.url):
                    _active_page.bring_to_front()
                    focus_browser_window()
                    is_root = parsed_target.path in ("", "/") and not parsed_target.query
                    if is_root:
                        return _active_page
                    if _active_page.url.rstrip("/") != target_url.rstrip("/"):
                        _active_page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                    return _active_page
        except Exception:
            _active_page = None

    if _active_browser is not None:
        try:
            for context in _active_browser.contexts:
                for page in context.pages:
                    if not page.is_closed() and is_matching(page.url):
                        _active_page = page
                        page.bring_to_front()
                        focus_browser_window()
                        is_root = parsed_target.path in ("", "/") and not parsed_target.query
                        if is_root:
                            return page
                        if page.url.rstrip("/") != target_url.rstrip("/"):
                            page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                        return page
        except Exception:
            pass

    if _active_page is not None:
        try:
            if not _active_page.is_closed():
                _active_page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                _active_page.bring_to_front()
                focus_browser_window()
                return _active_page
        except Exception:
            _active_page = None

    try:
        context = _active_browser.contexts[0] if _active_browser.contexts else _active_browser.new_context()
        _active_page = context.new_page()
        _active_page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
        _active_page.bring_to_front()
        focus_browser_window()
        return _active_page
    except Exception as e:
        logger.exception("Failed to open page")
        raise e

def open_url_in_browser_raw(url: str) -> str:
    """Opens a URL in the user's persistent, active desktop browser."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
        
    try:
        page = get_or_create_page(url)
        return f"✅ Navigated to '{url}' in your active browser window."
    except Exception as e:
        logger.warning("Playwright persistent browser failed, falling back to default system browser: %s", str(e))
        try:
            webbrowser.open(url)
            return f"✅ Opened '{url}' in your default system web browser."
        except Exception as e_fallback:
            return f"❌ Error opening browser: {str(e_fallback)}"

def search_youtube_raw(query: str) -> str:
    """Searches YouTube and AUTO-PLAYS the first video result in the persistent browser.
    
    Strategy:
    1. Open YouTube in persistent Playwright browser
    2. Search for the query  
    3. Get the first video's /watch?v=... URL
    4. Navigate directly to it with autoplay=1
    5. Force video.play() via JS to bypass browser autoplay policy
    """
    encoded = urllib.parse.quote(query)
    search_url = f"https://www.youtube.com/results?search_query={encoded}"

    try:
        # Check if the active page is already on YouTube
        page = None
        global _active_page
        if _active_page is not None:
            try:
                if not _active_page.is_closed() and "youtube.com" in _active_page.url.lower():
                    page = _active_page
                    page.bring_to_front()
                    focus_browser_window()
            except Exception:
                _active_page = None

        if page is None:
            page = get_or_create_page("https://www.youtube.com")

        # Navigate to search results page
        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        except Exception:
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)

        # Dismiss consent banners
        for btn in ["button:has-text('Accept all')", "button:has-text('I agree')",
                    "button:has-text('Reject all')", "[aria-label='Accept all']"]:
            try:
                page.click(btn, timeout=800)
            except Exception:
                pass

        # Wait for video results to appear
        page.wait_for_selector("ytd-video-renderer", timeout=15000)

        # Get the first video's title and watch URL
        first_video = page.locator("ytd-video-renderer a#video-title").first
        video_title = first_video.inner_text(timeout=5000).strip()
        video_href = first_video.get_attribute("href", timeout=3000) or ""

        if video_href:
            # Build direct watch URL with autoplay=1
            if video_href.startswith("/"):
                watch_url = f"https://www.youtube.com{video_href}"
            else:
                watch_url = video_href
            # Add autoplay parameter
            sep = "&" if "?" in watch_url else "?"
            watch_url = f"{watch_url}{sep}autoplay=1"

            # Navigate directly to the video page
            page.goto(watch_url, wait_until="domcontentloaded", timeout=20000)
        else:
            # Fallback: just click
            first_video.click()

        # Wait for the video element and force play
        try:
            page.wait_for_selector("video", timeout=12000)
            page.evaluate("""() => {
                const v = document.querySelector('video');
                if (v) {
                    v.muted = false;
                    v.volume = 1.0;
                    v.play().catch(() => {});
                }
            }""")
        except Exception:
            pass

        return f"✅ Now playing **'{video_title}'** on YouTube! 🎵"

    except Exception as e:
        logger.warning("Playwright YouTube failed, falling back to system browser: %s", str(e))
        try:
            fallback_url = f"https://www.youtube.com/results?search_query={encoded}"
            import subprocess
            _flags = 0
            if hasattr(subprocess, "DETACHED_PROCESS"):
                _flags |= subprocess.DETACHED_PROCESS
            brave_path = get_brave_path()
            if brave_path:
                subprocess.Popen(
                    [brave_path, fallback_url],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    close_fds=True,
                    creationflags=_flags,
                )
            else:
                webbrowser.open(fallback_url)
            return f"⚠️ Opened YouTube in your browser for **'{query}'**. Click the first video to play it."
        except Exception as e_fallback:
            return f"❌ Error opening YouTube: {str(e_fallback)}"

def web_search_raw(query: str) -> str:
    """Search the web for current information using DuckDuckGo HTML mode."""
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_web_search_sync_worker, query)
        return future.result()

def _web_search_sync_worker(query: str) -> str:
    try:
        from playwright.sync_api import sync_playwright

        is_news_request = any(
            term in query.lower()
            for term in ["news", "latest", "recent", "current", "update", "today", "now", "happening"]
        )

        search_query = query
        if is_news_request and "2026" not in query:
            search_query = f"{query} 2026"

        encoded = urllib.parse.quote(search_query)
        search_url = f"https://html.duckduckgo.com/html/?q={encoded}"
        if is_news_request:
            search_url += "&df=m"

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
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                }
            )
            page = context.new_page()
            page.goto(search_url, wait_until="domcontentloaded", timeout=20000)

            results = []
            page.wait_for_selector(".result", timeout=10000)
            items = page.locator(".result").all()[:5]

            for item in items:
                try:
                    title = ""
                    try:
                        title = item.locator(".result__title").inner_text(timeout=2000).strip()
                    except Exception:
                        pass

                    url = ""
                    try:
                        url = item.locator(".result__url").inner_text(timeout=2000).strip()
                    except Exception:
                        try:
                            url = item.locator(".result__a").get_attribute("href") or ""
                        except Exception:
                            pass

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

                    snippet = ""
                    try:
                        snippet = item.locator(".result__snippet").inner_text(timeout=2000).strip()
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
            return f"Search results for: {query}\n\n" + "\n\n---\n\n".join(results)
        return f"No relevant search results found for '{query}'."
    except Exception as e:
        return f"Error performing web search: {str(e)}"

def pause_playback_raw() -> str:
    """Pauses video or audio playback on the active browser page."""
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

def browser_navigate_raw(url: str) -> str:
    """Navigate to a URL using the active persistent browser tab."""
    try:
        page = get_active_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        return f"✅ Navigated to {url}"
    except Exception as e:
        return f"❌ Failed to navigate to {url}: {str(e)}"

def browser_click_raw(selector: str) -> str:
    """Click an element on the active persistent browser tab."""
    try:
        page = get_active_page()
        page.click(selector, timeout=10000)
        return f"✅ Clicked element: '{selector}'"
    except Exception as e:
        return f"❌ Failed to click element '{selector}': {str(e)}"

def browser_type_raw(selector: str, text: str) -> str:
    """Type text into an input element on the active persistent browser tab."""
    try:
        page = get_active_page()
        page.type(selector, text, timeout=10000)
        return f"✅ Typed text into element: '{selector}'"
    except Exception as e:
        return f"❌ Failed to type into element '{selector}': {str(e)}"

def browser_wait_for_raw(selector: str) -> str:
    """Wait for an element to be visible on the active persistent browser tab."""
    try:
        page = get_active_page()
        page.wait_for_selector(selector, timeout=10000)
        return f"✅ Element is visible: '{selector}'"
    except Exception as e:
        return f"❌ Element did not appear: '{selector}' ({str(e)})"

def browser_take_screenshot_raw(path: str) -> str:
    """Take a screenshot of the active persistent browser tab."""
    try:
        page = get_active_page()
        page.screenshot(path=path)
        return f"✅ Screenshot saved successfully to: '{path}'"
    except Exception as e:
        return f"❌ Failed to take screenshot: {str(e)}"

def browser_close_raw() -> str:
    """Close the active persistent browser tab and process gracefully."""
    if close_persistent_browser():
        return "✅ Persistent browser closed successfully."
    return "ℹ️ No persistent browser was running."

def browser_scroll_raw(direction: str = "down", amount: int = 500) -> str:
    """Scroll the active persistent browser page."""
    try:
        page = get_active_page()
        dir_lower = direction.lower().strip()
        if dir_lower == "down":
            page.evaluate(f"window.scrollBy(0, {amount})")
        elif dir_lower == "up":
            page.evaluate(f"window.scrollBy(0, -{amount})")
        elif dir_lower == "left":
            page.evaluate(f"window.scrollBy(-{amount}, 0)")
        elif dir_lower == "right":
            page.evaluate(f"window.scrollBy({amount}, 0)")
        else:
            return f"❌ Invalid scroll direction: {direction}"
        return f"✅ Scrolled {dir_lower} by {amount} pixels."
    except Exception as e:
        return f"❌ Failed to scroll browser: {str(e)}"

def browser_extract_text_raw() -> str:
    """Extract all visible text content from the active browser page."""
    try:
        page = get_active_page()
        text = page.evaluate("document.body.innerText")
        if not text or not text.strip():
            return "No text content found on the page."
        if len(text) > 10000:
            return text[:10000] + "\n\n[... Page content truncated ...]"
        return text.strip()
    except Exception as e:
        return f"❌ Failed to extract text from page: {str(e)}"

def resume_playback_raw() -> str:
    """Resumes video or audio playback on the active browser page."""
    global _active_page
    if _active_page is not None:
        try:
            if not _active_page.is_closed():
                _active_page.bring_to_front()
                focus_browser_window()
                _active_page.evaluate("""() => {
                    const v = document.querySelector('video');
                    if (v) {
                        v.play().catch(() => {});
                    } else {
                        // Click first video link on search results page as fallback
                        const firstVideo = document.querySelector('ytd-video-renderer a#video-title, a[href*="/watch?v="]');
                        if (firstVideo) {
                            firstVideo.click();
                        }
                    }
                }""")
                return "✅ Started playing (resumed video playback on the active browser tab)."
        except Exception as e:
            return f"❌ Failed to play video: {str(e)}"
    return "ℹ️ No active browser tab was open to play."

def list_browser_tabs_raw() -> str:
    """Lists all open tabs in the persistent browser and indicates the active one."""
    global _active_browser, _active_page
    if not _active_browser:
        return "No persistent browser is currently running."
        
    output = []
    tab_index = 0
    
    try:
        for context in _active_browser.contexts:
            for page in context.pages:
                if not page.is_closed():
                    title = page.title() or "Untitled"
                    url = page.url
                    is_active = (page == _active_page)
                    if is_active:
                        output.append(f"[{tab_index}] *ACTIVE* {title} - {url}")
                    else:
                        output.append(f"[{tab_index}] {title} - {url}")
                    tab_index += 1
                    
        if not output:
            return "No open tabs found."
            
        return "Open Browser Tabs:\n" + "\n".join(output)
    except Exception as e:
        return f"Failed to list browser tabs: {str(e)}"

def switch_browser_tab_raw(index: int) -> str:
    """Switches the active browser tab to the given index."""
    global _active_browser, _active_page
    if not _active_browser:
        return "No persistent browser is currently running."
        
    try:
        tab_index = 0
        for context in _active_browser.contexts:
            for page in context.pages:
                if not page.is_closed():
                    if tab_index == index:
                        _active_page = page
                        _active_page.bring_to_front()
                        focus_browser_window()
                        return f"✅ Switched active tab to: {page.title()} ({page.url})"
                    tab_index += 1
                    
        return f"❌ Tab index {index} is out of range."
    except Exception as e:
        return f"❌ Failed to switch tab: {str(e)}"
