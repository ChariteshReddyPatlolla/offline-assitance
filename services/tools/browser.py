"""
YouTube automation and web search tools using Playwright.
Falls back to webbrowser.open if Playwright is unavailable.
"""
import logging
import urllib.parse
import webbrowser
from langchain_core.tools import tool

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
    Searches YouTube for a query, opens the first video result, and starts playback automatically.
    Use this when the user wants to play music, watch a video, or search YouTube.
    Examples: 'play lofi music', 'play Taylor Swift songs', 'play relaxing music on youtube'
    """
    try:
        from playwright.sync_api import sync_playwright

        encoded = urllib.parse.quote(query)
        search_url = f"https://www.youtube.com/results?search_query={encoded}"

        video_url = None
        video_title = None

        with sync_playwright() as p:
            # Use the installed Google Chrome instead of bundled Chromium
            browser = p.chromium.launch(channel="chrome", headless=True, args=["--no-sandbox"])
            page = browser.new_page()
            
            logger.info("Opening YouTube search headless: %s", search_url)
            page.goto(search_url, wait_until="domcontentloaded", timeout=20000)

            # Dismiss cookie consent if present
            try:
                page.click("button:has-text('Accept all')", timeout=3000)
            except Exception:
                pass
            try:
                page.click("button:has-text('Reject all')", timeout=1000)
            except Exception:
                pass

            # Wait for video thumbnails to load
            page.wait_for_selector("ytd-video-renderer", timeout=15000)

            # Click the first video result (not ads, not shorts)
            first_video = page.locator("ytd-video-renderer a#video-title").first
            video_title = first_video.inner_text(timeout=5000).strip()
            video_url = first_video.get_attribute("href")
            
            browser.close()

        if video_url:
            if not video_url.startswith("http"):
                video_url = "https://www.youtube.com" + video_url
            
            # Autoplay parameter
            if "?" in video_url:
                video_url += "&autoplay=1"
            else:
                video_url += "?autoplay=1"
                
            # Open in system browser so it NEVER closes
            _open_in_chrome(video_url)
            
            logger.info("Playing YouTube video in system browser: %s", video_title)
            return (
                f"✅ Playing **\"{video_title}\"** on YouTube for query: *{query}*\n\n"
                f"The video is now playing in your default browser."
            )
        else:
            return f"❌ Could not find any videos for '{query}'"

    except ImportError:
        # Playwright not installed — open search in system browser
        encoded = urllib.parse.quote(query)
        url = f"https://www.youtube.com/results?search_query={encoded}"
        _open_in_chrome(url)
        return (
            f"⚠️ Playwright not installed (run `playwright install chromium` to enable auto-play). "
            f"Opened YouTube search for *{query}* in your browser."
        )
    except Exception as e:
        logger.error("YouTube automation error: %s", e)
        # Fallback: open search in browser
        try:
            encoded = urllib.parse.quote(query)
            _open_in_chrome(f"https://www.youtube.com/results?search_query={encoded}")
            return f"⚠️ Auto-play failed ({e}). Opened YouTube search for *{query}* in Google Chrome."
        except Exception as fe:
            return f"❌ Error opening YouTube: {str(fe)}"


@tool
def web_search(query: str) -> str:
    """
    Search the web for information using DuckDuckGo. Returns titles, URLs and text snippets.
    Use this to look up facts, tutorials, news, or any information.
    """
    try:
        from playwright.sync_api import sync_playwright
        encoded = urllib.parse.quote(query)
        
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True, args=["--no-sandbox"])
            page = browser.new_page()
            page.goto(f"https://duckduckgo.com/?q={encoded}", wait_until="domcontentloaded", timeout=15000)

            # Try extracting results
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
                        results.append(f"**{title}**\n{url}\n{snippet}")
                    except Exception:
                        pass
            except Exception:
                results = [page.locator("body").inner_text()[:1500]]
            
            browser.close()

        if results:
            return f"🔍 **Search results for '{query}':**\n\n" + "\n\n---\n\n".join(results)
        return f"No results found for '{query}'."

    except ImportError:
        encoded = urllib.parse.quote(query)
        _open_in_chrome(f"https://duckduckgo.com/?q={encoded}")
        return f"✅ Opened DuckDuckGo search for '{query}' in Google Chrome."
    except Exception as e:
        try:
            encoded = urllib.parse.quote(query)
            _open_in_chrome(f"https://duckduckgo.com/?q={encoded}")
            return f"⚠️ Search opened in Google Chrome for '{query}'. ({e})"
        except Exception:
            return f"❌ Error performing web search: {str(e)}"
