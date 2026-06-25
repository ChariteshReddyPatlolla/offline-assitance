import re
import os
import time
import uuid
import logging
import difflib

def return_focus_if_omniagent():
    import ctypes
    import pyautogui
    import time
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value.lower()
        if "omniagent" in title or "frontend" in title or "react" in title or "chat.py" in title:
            pyautogui.hotkey("alt", "tab")
            time.sleep(0.1)
    except Exception:
        pass

logger = logging.getLogger(__name__)

# Initialize fast spellchecker for typo tolerance on targets
try:
    from spellchecker import SpellChecker
    fast_spell = SpellChecker()
    # Add common tech terms to prevent false-positive corrections
    fast_spell.word_frequency.load_words([
        "leetcode", "whatsapp", "vscode", "youtube", "github", "chatgpt", "claude", 
        "gemini", "spotify", "chrome", "edge", "netflix", "facebook", "twitter", 
        "instagram", "tiktok", "amazon", "flipkart"
    ])
    def spellcheck_target(text):
        if not text: return text
        words = text.split()
        corrected = []
        for w in words:
            corr = fast_spell.correction(w)
            corrected.append(corr if corr else w)
        return " ".join(corrected)
except ImportError:
    # Fallback if pyspellchecker isn't installed
    def spellcheck_target(text):
        return text

command_prefixes = [
    "open", "create file", "make file", "search on youtube", "play on youtube",
    "search youtube for", "play youtube for", "search for", "type and search", "type",
    "lock screen", "lock pc", "lock computer", "show desktop", "minimize all",
    "volume up", "volume down", "volume mute", "volume max",
    "take a screenshot", "take screenshot", "screenshot",
    "play", "pause", "play it", "pause it", "play the video", "pause the video", "play song", "pause song", "next track", "previous track", "skip",
    "go to", "new tab", "close tab", "go back", "back", 
    "open first link", "open second link", "open third link", "open 1st link", "open it",
    "close this", "minimize this", "maximize this", "refresh this", "reload this",
    "click on", "close", "switch to",
    "write a script", "write script", "write code", "update the code", "change the code", "rewrite the code", "modify the code", "add a line", "add a like", "also add", "also update", "also change", "also modify", "delete", "delete the line", "delete the part", "remove", "remove a line", "also delete", "also remove",
    "run the code", "run code", "run script", "run file", "run this", "run it", "run",
    "show me it", "paste the code", "paste it",
    "open downloads", "open documents", "open pictures", "open desktop", "open music",
    "empty recycle bin", "empty the recycle bin",
    "check security", "scan system", "security check", "scan for backdoors"
]

def fix_typos(text):
    words = text.split()
    
    # Pass 1: Exact matches (longest prefix first)
    for i in [3, 2, 1]:
        if len(words) >= i:
            prefix = " ".join(words[:i]).lower()
            if prefix in command_prefixes:
                return text
                
    # Pass 2: Fuzzy matches (longest prefix first)
    for i in [3, 2, 1]:
        if len(words) >= i:
            prefix = " ".join(words[:i]).lower()
            matches = difflib.get_close_matches(prefix, command_prefixes, n=1, cutoff=0.7)
            if matches:
                return matches[0] + " " + " ".join(words[i:])
                
    return text

def process_fast_path_commands(clauses: list[str]) -> tuple[str | None, list[dict]]:
    """
    Evaluates the parsed clauses and executes fast-path commands.
    Returns a tuple of (response_message, tool_calls_list).
    If no fast-paths are triggered, returns (None, []).
    """
    if not clauses:
        return None, []

    clauses = [fix_typos(c.strip()) for c in clauses if c.strip()]
    
    # Pre-check all clauses to ensure they are fast-path commands
    all_fast_paths = True
    for c in clauses:
        ml = c.lower()
        if not any([
            re.match(r"^open\s+(.+)$", ml),
            re.match(r"^(?:create|make)\s+file\s+(.+)$", ml),
            re.match(r"^(?:search|play)\s+(?:on\s+)?(?:youtube|yt)\s+(?:for\s+)?(.+)$", ml),
            re.match(r"^(?:search|play)\s+(.+?)\s+(?:on\s+)?(?:youtube|yt)$", ml),
            re.match(r"^(?:type and search|search for)\s+(.+)$", ml),
            re.match(r"^type\s+(.+)$", ml),
            re.match(r"^lock\s+(?:the\s+)?(?:screen|pc|computer|system)$", ml),
            re.match(r"^(?:show\s+(?:the\s+)?desktop|minimize\s+all)$", ml),
            re.match(r"^(?:volume|vol)\s+(up|down|mute|max)$", ml),
            re.match(r"^(?:take\s+a\s+)?screenshot$", ml),
            re.match(r"^(?:play|pause)(?:\s+(?:the\s+)?(?:video|audio|song|music|media|it|playback))?$|^(?:next|previous)\s+track$|^skip$", ml),
            re.match(r"^(go back|back)$", ml),
            re.match(r"^(?:go\s+to|open)\s+([a-z0-9.-]+\.[a-z]{2,})(?:\s.*)?$", ml),
            re.match(r"^(?:open|go\s+to)\s+(.+)\s+(?:website|site|page)$", ml),
            re.match(r"^(new tab|close tab)$", ml),
            re.match(r"^open\s+(?:the\s+)?(first|second|third|1st|2nd|3rd)\s+link$|^open\s+it$", ml),
            re.match(r"^(close|minimize|maximize|refresh|reload)\s+(?:this|current|it)(?:\s+(window|tab|app|application|page))?$", ml),
            re.match(r"^(?:click\s+(?:on\s+)?|go\s+to\s+)(.+)$", ml),
            re.match(r"^close\s+(.+)$", ml),
            re.match(r"^switch\s+to\s+(.+)$", ml),
            re.match(r"^write\s+(?:me\s+)?(?:a\s+|an\s+)?(.*?(?:script|code|program)\b.*)$", ml),
            re.match(r"^(?:also\s+)?(?:update|change|rewrite|modify|add|delete|remove)\b(.*)$", ml),
            re.match(r"^run\s+(?:the\s+)?(?:code|script|file|this|it)$", ml),
            re.match(r"^(show me it|paste the code|paste it)$", ml),
            re.match(r"^run\s+(.+\.[a-z0-9]+)$", ml),
            re.match(r"^open\s+(downloads|documents|pictures|desktop|music)$", ml),
            re.match(r"^open\s+([a-z])\s+drive$", ml),
            re.match(r"^empty\s+(?:the\s+)?recycle\s+bin$", ml),
            re.match(r"^(?:check\s+security|scan\s+system|security\s+check|scan\s+for\s+backdoors)$", ml)
        ]):
            all_fast_paths = False
            break

    if not all_fast_paths:
        return None, []

    fast_path_tool_calls = []
    responses = []
    
    for i, clause in enumerate(clauses):
        if i > 0:
            time.sleep(1.0)
            
        msg_lower = clause.lower()
        request_message = clause 
        fast_path_response = None
        
        # Matches
        open_app_match = re.match(r"^open\s+(.+)$", msg_lower)
        create_file_match = re.match(r"^(?:create|make)\s+file\s+(.+)$", msg_lower)
        yt_match_1 = re.match(r"^(?:search|play)\s+(?:on\s+)?(?:youtube|yt)\s+(?:for\s+)?(.+)$", msg_lower)
        yt_match_2 = re.match(r"^(?:search|play)\s+(.+?)\s+(?:on\s+)?(?:youtube|yt)$", msg_lower)
        type_enter_match = re.match(r"^(?:type and search|search for)\s+(.+)$", msg_lower)
        type_only_match = re.match(r"^type\s+(.+)$", msg_lower)
        lock_match = re.match(r"^lock\s+(?:the\s+)?(?:screen|pc|computer|system)$", msg_lower)
        desktop_match = re.match(r"^(?:show\s+(?:the\s+)?desktop|minimize\s+all)$", msg_lower)
        vol_match = re.match(r"^(?:volume|vol)\s+(up|down|mute|max)$", msg_lower)
        screenshot_match = re.match(r"^(?:take\s+a\s+)?screenshot$", msg_lower)
        media_match = re.match(r"^(play|pause)(?:\s+(?:the\s+)?(?:video|audio|song|music|media|it|playback))?$|^(next|previous)\s+track$|^(skip)$", msg_lower)
        back_match = re.match(r"^(go back|back)$", msg_lower)
        go_match = re.match(r"^(?:go\s+to|open)\s+([a-z0-9.-]+\.[a-z]{2,})(?:\s.*)?$", msg_lower)
        website_match = re.match(r"^(?:open|go\s+to)\s+(.+)\s+(?:website|site|page)$", msg_lower)
        tab_match = re.match(r"^(new tab|close tab)$", msg_lower)
        link_match = re.match(r"^open\s+(?:the\s+)?(first|second|third|1st|2nd|3rd)\s+link$", msg_lower)
        this_match = re.match(r"^(close|minimize|maximize|refresh|reload)\s+(?:this|current|it)(?:\s+(window|tab|app|application|page))?$", msg_lower)
        click_match = re.match(r"^(?:click\s+(?:on\s+)?|go\s+to\s+)(.+)$", msg_lower)
        close_app_match = re.match(r"^close\s+(.+)$", msg_lower)
        switch_app_match = re.match(r"^switch\s+to\s+(.+)$", msg_lower)
        write_macro_match = re.match(r"^write\s+(?:me\s+)?(?:a\s+|an\s+)?(.*?(?:script|code|program)\b.*)$", msg_lower)
        update_macro_match = re.match(r"^(?:also\s+)?(?:update|change|rewrite|modify|add|delete|remove)\b(.*)$", msg_lower)
        run_code_match = re.match(r"^run\s+(?:the\s+)?(?:code|script|file|this|it)$", msg_lower)
        show_me_match = re.match(r"^(show me it|paste the code|paste it)$", msg_lower)
        run_file_match = re.match(r"^run\s+(.+\.[a-z0-9]+)$", msg_lower)
        folder_match = re.match(r"^open\s+(downloads|documents|pictures|desktop|music)$", msg_lower)
        drive_match = re.match(r"^open\s+([a-z])\s+drive$", msg_lower)
        recycle_match = re.match(r"^empty\s+(?:the\s+)?recycle\s+bin$", msg_lower)
        security_match = re.match(r"^(?:check\s+security|scan\s+system|security\s+check|scan\s+for\s+backdoors)$", msg_lower)

        yt_query = None
        if yt_match_1:
            yt_query = spellcheck_target(yt_match_1.group(1).strip())
        elif yt_match_2:
            yt_query = spellcheck_target(yt_match_2.group(1).strip())

        if lock_match:
            try:
                import ctypes
                ctypes.windll.user32.LockWorkStation()
                fast_path_response = "Locked the screen (Fast-path)."
            except Exception as e:
                logger.warning("Fast-path lock screen failed: %s", e)
        
        elif desktop_match:
            try:
                import pyautogui
                pyautogui.hotkey('win', 'd')
                fast_path_response = "Showing desktop (Fast-path)."
            except Exception as e:
                logger.warning("Fast-path show desktop failed: %s", e)

        elif vol_match:
            action = vol_match.group(1)
            try:
                import pyautogui
                if action == "up":
                    pyautogui.press("volumeup", presses=5)
                    fast_path_response = "Increased volume (Fast-path)."
                elif action == "down":
                    pyautogui.press("volumedown", presses=5)
                    fast_path_response = "Decreased volume (Fast-path)."
                elif action == "mute":
                    pyautogui.press("volumemute")
                    fast_path_response = "Toggled mute (Fast-path)."
                elif action == "max":
                    pyautogui.press("volumeup", presses=50)
                    fast_path_response = "Maximized volume (Fast-path)."
            except Exception as e:
                logger.warning("Fast-path volume control failed: %s", e)

        elif screenshot_match:
            try:
                import pyautogui
                pyautogui.hotkey('win', 'prtsc')
                fast_path_response = "Took a screenshot (Fast-path). It is saved in your Pictures\\Screenshots folder."
            except Exception as e:
                logger.warning("Fast-path screenshot failed: %s", e)

        elif media_match:
            action = next(g for g in media_match.groups() if g is not None)
            try:
                import pyautogui
                if action in ["play", "pause"]:
                    pyautogui.press("playpause")
                    fast_path_response = "Toggled media playback (Fast-path)."
                elif action in ["next", "skip"]:
                    pyautogui.press("nexttrack")
                    fast_path_response = "Skipped to next track (Fast-path)."
                elif action == "previous":
                    pyautogui.press("prevtrack")
                    fast_path_response = "Went to previous track (Fast-path)."
            except Exception as e:
                logger.warning("Fast-path media control failed: %s", e)

        elif back_match:
            try:
                import pyautogui
                pyautogui.press("browserback")
                fast_path_response = "Went back (Fast-path)."
            except Exception as e:
                logger.warning("Fast-path go back failed: %s", e)

        elif go_match:
            website = spellcheck_target(go_match.group(1).strip())
            try:
                import webbrowser
                url = f"https://{website}" if not website.startswith("http") else website
                webbrowser.open(url)
                fast_path_response = f"Opened {website} in your browser (Fast-path)."
            except Exception as e:
                logger.warning("Fast-path go to website failed: %s", e)

        elif website_match:
            query = spellcheck_target(website_match.group(1).strip())
            try:
                import urllib.parse
                import webbrowser
                search_url = f"https://duckduckgo.com/?q=%5C{urllib.parse.quote(query + ' website')}"
                webbrowser.open(search_url)
                fast_path_response = f"Opening the {query} website (Fast-path)."
            except Exception as e:
                logger.warning("Fast-path open website failed: %s", e)

        elif tab_match:
            action = tab_match.group(1)
            try:
                import pyautogui
                return_focus_if_omniagent()
                if action == "new tab":
                    pyautogui.hotkey("ctrl", "t")
                    fast_path_response = "Opened a new browser tab (Fast-path)."
                elif action == "close tab":
                    pyautogui.hotkey("ctrl", "w")
                    fast_path_response = "Closed the current browser tab (Fast-path)."
            except Exception as e:
                logger.warning("Fast-path tab management failed: %s", e)

        elif link_match:
            link_pos = link_match.group(1).lower() if link_match.group(1) else 'first'
            try:
                import pyautogui
                return_focus_if_omniagent()
                presses = 1
                if link_pos in ["second", "2nd"]: presses = 2
                elif link_pos in ["third", "3rd"]: presses = 3
                for _ in range(presses):
                    pyautogui.press("down")
                    time.sleep(0.1)
                time.sleep(0.1)
                pyautogui.press("enter")
                fast_path_response = f"Opened the {link_pos} link (Fast-path)."
            except Exception as e:
                logger.warning("Fast-path open link failed: %s", e)

        elif click_match:
            link_text = spellcheck_target(click_match.group(1).strip())
            try:
                import pyautogui
                return_focus_if_omniagent()
                pyautogui.hotkey("ctrl", "f")
                time.sleep(0.1)
                pyautogui.write(link_text, interval=0.01)
                time.sleep(0.2)
                pyautogui.press("esc")
                time.sleep(0.1)
                pyautogui.press("enter")
                fast_path_response = f"Attempted to click on '{link_text}' (Fast-path)."
            except Exception as e:
                logger.warning("Fast-path click link failed: %s", e)

        elif this_match:
            action = this_match.group(1)
            target = this_match.group(2) or ""
            try:
                import pyautogui
                return_focus_if_omniagent()
                if action == "close":
                    if target in ["app", "application", "window"]:
                        pyautogui.hotkey("alt", "f4")
                        fast_path_response = "Closed the current window/app (Fast-path)."
                    else:
                        pyautogui.hotkey("ctrl", "w")
                        fast_path_response = "Closed the current tab/document (Fast-path)."
                elif action == "minimize":
                    pyautogui.hotkey("win", "down")
                    pyautogui.hotkey("win", "down")
                    fast_path_response = "Minimized the current window (Fast-path)."
                elif action == "maximize":
                    pyautogui.hotkey("win", "up")
                    fast_path_response = "Maximized the current window (Fast-path)."
                elif action in ["refresh", "reload"]:
                    pyautogui.press("f5")
                    fast_path_response = "Refreshed the current page/window (Fast-path)."
            except Exception as e:
                logger.warning("Fast-path 'this' action failed: %s", e)

        elif create_file_match:
            prefix_len = create_file_match.end(0) - len(create_file_match.group(1))
            filename = request_message.strip()[prefix_len:].strip()
            try:
                if not os.path.isabs(filename):
                    desktop_path = os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop', 'offline_llm')
                    if not os.path.exists(desktop_path):
                        os.makedirs(desktop_path, exist_ok=True)
                    filepath = os.path.join(desktop_path, filename)
                else:
                    filepath = os.path.abspath(filename)
                if not os.path.exists(filepath):
                    with open(filepath, 'w') as f:
                        f.write("")
                os.startfile(filepath)
                fast_path_response = f"Created and opened '{filename}' (Fast-path)."
                fast_path_tool_calls.append({"name": "write_file", "args": {"filepath": filename, "content": ""}, "id": str(uuid.uuid4())})
            except Exception as e:
                logger.warning("Fast-path create file failed: %s", e)

        elif write_macro_match:
            task = write_macro_match.group(1).strip()
            try:
                from langchain_ollama import ChatOllama
                from langchain_core.messages import HumanMessage
                fast_llm = ChatOllama(model="llama3.2:latest", temperature=0.1, keep_alive=-1)
                import asyncio
                
                # Execute asynchronously by running the async function in the synchronous context via asyncio run if needed
                # Wait! We're not inside async def here, fast paths run sync.
                try:
                    # Let's get the event loop to run it
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # We cannot do loop.run_until_complete if loop is running. 
                        # Using invoke instead of ainvoke
                        ai_msg = fast_llm.invoke([
                            HumanMessage(content=f"Write a {task}. Output ONLY the raw code. Do NOT wrap it in markdown block quotes (e.g. no ```python). Do NOT add any explanations or comments outside the code.")
                        ])
                    else:
                        ai_msg = loop.run_until_complete(fast_llm.ainvoke([
                            HumanMessage(content=f"Write a {task}. Output ONLY the raw code. Do NOT wrap it in markdown block quotes (e.g. no ```python). Do NOT add any explanations or comments outside the code.")
                        ]))

                except Exception:
                    # Fallback to sync invoke
                    ai_msg = fast_llm.invoke([
                        HumanMessage(content=f"Write a {task}. Output ONLY the raw code. Do NOT wrap it in markdown block quotes (e.g. no ```python). Do NOT add any explanations or comments outside the code.")
                    ])
                    
                raw_code = ai_msg.content.strip()
        
                if raw_code.startswith("```"):
                    lines = raw_code.split("\n")
                    if len(lines) >= 2:
                        lines = lines[1:] 
                        if lines and lines[-1].startswith("```"):
                            lines = lines[:-1]
                    raw_code = "\n".join(lines).strip()
            
                ext = ".py"
                t_lower = task.lower()
                if "javascript" in t_lower or "js" in t_lower or "node" in t_lower: ext = ".js"
                elif "html" in t_lower: ext = ".html"
                elif "cpp" in t_lower or "c++" in t_lower: ext = ".cpp"
                elif "java" in t_lower: ext = ".java"
                elif "bash" in t_lower or "shell" in t_lower: ext = ".sh"
                elif "bat" in t_lower: ext = ".bat"
        
                filename = f"generated_{task.replace(' ', '_').replace('/', '_')[:20]}{ext}"
                desktop_path = os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop', 'offline_llm')
                if not os.path.exists(desktop_path):
                    os.makedirs(desktop_path, exist_ok=True)
                filepath = os.path.join(desktop_path, filename)
        
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(raw_code)
            
                import shared.context
                shared.context.last_generated_file = filepath
            
                from services.tools.impl.desktop import open_file_in_vscode_raw
                open_file_in_vscode_raw(filepath)
        
                fast_path_response = f"Successfully generated '{task}' code, saved it to {filename}, and opened it in VS Code! Say 'run the code' to execute it."
            except Exception as e:
                logger.warning("Fast-path write code macro failed: %s", e)
        elif update_macro_match:
            task = msg_lower.strip()
            try:
                import shared.context
                from langchain_ollama import ChatOllama
                from langchain_core.messages import HumanMessage
                
                filepath = getattr(shared.context, 'last_generated_file', None)
                if filepath and os.path.exists(filepath):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        existing_code = f.read()
                        
                    fast_llm = ChatOllama(model="llama3.2:latest", temperature=0.1, keep_alive=-1)
                    prompt = f"Existing code:\n```\n{existing_code}\n```\n\nTask: {task}\n\nRewrite the code to fulfill the task. Output ONLY the raw updated code. Do NOT wrap it in markdown block quotes (e.g. no ```python). Do NOT add any explanations or comments outside the code."
                    
                    try:
                        import asyncio
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            ai_msg = fast_llm.invoke([HumanMessage(content=prompt)])
                        else:
                            ai_msg = loop.run_until_complete(fast_llm.ainvoke([HumanMessage(content=prompt)]))
                    except Exception:
                        ai_msg = fast_llm.invoke([HumanMessage(content=prompt)])
                        
                    raw_code = ai_msg.content.strip()
            
                    if raw_code.startswith("```"):
                        lines = raw_code.split("\n")
                        if len(lines) >= 2:
                            lines = lines[1:] 
                            if lines and lines[-1].startswith("```"):
                                lines = lines[:-1]
                        raw_code = "\n".join(lines).strip()
                        
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(raw_code)
                        
                    fast_path_response = f"Successfully updated your code in {os.path.basename(filepath)}!"
                else:
                    fast_path_response = "I don't know which file to update. Please generate a file first using 'write a python code...'."
            except Exception as e:
                logger.warning("Fast-path update code macro failed: %s", e)
        elif show_me_match:
            try:
                import redis
                import json
                import ctypes
                import pyautogui
                from shared.context import current_session_id
                
                # Fetch result from Redis
                session_id = current_session_id.get()
                r = redis.Redis(host='localhost', port=6379, db=0, protocol=2)
                result_bytes = r.get(f"llm_result:{session_id}")
                
                if result_bytes:
                    data = json.loads(result_bytes.decode('utf-8'))
                    code = data.get("code", "")
                    target_hwnd = data.get("target_hwnd")
                    
                    if code:
                        # Switch to the target window
                        if target_hwnd:
                            ctypes.windll.user32.SetForegroundWindow(target_hwnd)
                            time.sleep(0.2)
                        else:
                            return_focus_if_omniagent()
                            time.sleep(0.2)
                            
                        # Undo the "// Model is thinking..." indicator
                        pyautogui.hotkey("ctrl", "z")
                        time.sleep(0.1)
                        
                        # Copy code to clipboard and paste
                        import pyperclip
                        original_clipboard = pyperclip.paste()
                        pyperclip.copy(code)
                        pyautogui.hotkey("ctrl", "v")
                        time.sleep(0.1)
                        pyperclip.copy(original_clipboard) # Restore user's clipboard
                        
                        # Clear Redis key
                        r.delete(f"llm_result:{session_id}")
                        fast_path_response = "I have successfully pasted the code into your editor!"
                    else:
                        fast_path_response = "The model finished, but no code was found."
                else:
                    fast_path_response = "There is no completed code generation task waiting."
            except Exception as e:
                logger.warning("Fast-path show me failed: %s", e)
                fast_path_response = f"Failed to paste code. Error: {str(e)}"

        elif run_code_match:
            try:
                import pyautogui
                return_focus_if_omniagent()
                pyautogui.hotkey("ctrl", "f5")
                fast_path_response = "Switched to your editor and pressed 'Run' (Ctrl+F5) to execute the code inside VS Code."
            except Exception as e:
                logger.warning("Fast-path run code failed: %s", e)

        elif run_file_match:
            filename = run_file_match.group(1).strip()
            try:
                import subprocess
                filepath = os.path.abspath(filename)
                fast_path_run_resp = None
                if os.path.exists(filepath):
                    ext = os.path.splitext(filepath)[1].lower()
                    cmd = None
                    if ext == '.py':
                        cmd = f'python "{filepath}"'
                    elif ext == '.js':
                        cmd = f'node "{filepath}"'
                    elif ext in ['.bat', '.cmd', '.exe']:
                        cmd = f'"{filepath}"'
                    elif ext == '.html':
                        os.startfile(filepath)
                        fast_path_run_resp = f"Opened {filename} in browser (Fast-path)."
            
                    if cmd:
                        subprocess.Popen(f'start cmd /k {cmd}', shell=True)
                        fast_path_run_resp = f"Running {filename} in a new terminal (Fast-path)."
                    elif not fast_path_run_resp:
                        os.startfile(filepath)
                        fast_path_run_resp = f"Executed {filename} (Fast-path)."
                else:
                    fast_path_run_resp = f"Could not find '{filename}' to run."
                fast_path_response = fast_path_run_resp
            except Exception as e:
                logger.warning("Fast-path run file failed: %s", e)

        elif folder_match:
            folder = folder_match.group(1)
            try:
                user_profile = os.environ.get('USERPROFILE')
                folder_path = os.path.join(user_profile, folder.capitalize())
                os.startfile(folder_path)
                fast_path_response = f"Opened your {folder.capitalize()} folder (Fast-path)."
            except Exception as e:
                logger.warning("Fast-path open folder failed: %s", e)

        elif drive_match:
            drive_letter = drive_match.group(1).upper()
            try:
                drive_path = f"{drive_letter}:\\"
                if os.path.exists(drive_path):
                    os.startfile(drive_path)
                    fast_path_response = f"Opened {drive_letter}:\\ drive (Fast-path)."
                else:
                    fast_path_response = f"Drive {drive_letter}:\\ does not exist on this machine."
            except Exception as e:
                logger.warning("Fast-path open drive failed: %s", e)

        elif recycle_match:
            try:
                import ctypes
                shell32 = ctypes.windll.shell32
                shell32.SHEmptyRecycleBinW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32]
                shell32.SHEmptyRecycleBinW.restype = ctypes.c_long
                result = shell32.SHEmptyRecycleBinW(None, None, 7)
                if result == 0 or result == -2147418113:
                    fast_path_response = "Emptied the recycle bin (Fast-path)."
                else:
                    fast_path_response = f"Could not empty recycle bin. Error code: {result}"
            except Exception as e:
                logger.warning("Fast-path recycle bin failed: %s", e)
        
        elif close_app_match:
            app_name = spellcheck_target(close_app_match.group(1).strip())
            try:
                import ctypes
                EnumWindows = ctypes.windll.user32.EnumWindows
                EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
                GetWindowText = ctypes.windll.user32.GetWindowTextW
                GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
                IsWindowVisible = ctypes.windll.user32.IsWindowVisible

                WM_CLOSE = 0x0010
                closed_any = False

                def foreach_window(hwnd, lParam):
                    nonlocal closed_any
                    if IsWindowVisible(hwnd):
                        length = GetWindowTextLength(hwnd)
                        if length > 0:
                            buff = ctypes.create_unicode_buffer(length + 1)
                            GetWindowText(hwnd, buff, length + 1)
                            if app_name.lower() in buff.value.lower():
                                ctypes.windll.user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
                                closed_any = True
                    return True

                EnumWindows(EnumWindowsProc(foreach_window), 0)
        
                if closed_any:
                    fast_path_response = f"Sent close command to windows matching '{app_name}' (Fast-path)."
                else:
                    import subprocess
                    subprocess.Popen(f'taskkill /F /IM {app_name}.exe /T', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    fast_path_response = f"Attempted to force close '{app_name}' (Fast-path)."
            
            except Exception as e:
                logger.warning("Fast-path close app failed: %s", e)
        
        elif switch_app_match:
            app_name = spellcheck_target(switch_app_match.group(1).strip())
            try:
                import ctypes
                EnumWindows = ctypes.windll.user32.EnumWindows
                EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
                GetWindowText = ctypes.windll.user32.GetWindowTextW
                GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
                IsWindowVisible = ctypes.windll.user32.IsWindowVisible
                SetForegroundWindow = ctypes.windll.user32.SetForegroundWindow
                ShowWindow = ctypes.windll.user32.ShowWindow

                SW_RESTORE = 9
                switched_any = False

                def foreach_window(hwnd, lParam):
                    nonlocal switched_any
                    if not switched_any and IsWindowVisible(hwnd):
                        length = GetWindowTextLength(hwnd)
                        if length > 0:
                            buff = ctypes.create_unicode_buffer(length + 1)
                            GetWindowText(hwnd, buff, length + 1)
                            if app_name.lower() in buff.value.lower():
                                ShowWindow(hwnd, SW_RESTORE)
                                SetForegroundWindow(hwnd)
                                switched_any = True
                    return True

                EnumWindows(EnumWindowsProc(foreach_window), 0)
        
                if switched_any:
                    fast_path_response = f"Switched to '{app_name}' (Fast-path)."
                else:
                    fast_path_response = f"Could not find an open window matching '{app_name}'."
            except Exception as e:
                logger.warning("Fast-path switch app failed: %s", e)

        elif open_app_match:
            app_name = spellcheck_target(open_app_match.group(1).strip())
            app_query = app_name.lower()
    
            if app_query in ["vscode", "vs code", "code"]:
                app_query = "visual studio code"
            elif app_query in ["chrome", "google chrome"]:
                app_query = "chrome"
        
            try:
                import pyautogui
                pyautogui.press('win')
                time.sleep(0.5)
                pyautogui.write(app_name, interval=0.05)
                time.sleep(0.5)
                pyautogui.press('enter')
        
                fast_path_response = f"Searched for and attempted to open '{app_name}' via Windows Search (Fast-path)."
                fast_path_tool_calls.append({"name": "open_application", "args": {"app_name": app_name}, "id": str(uuid.uuid4())})
            except Exception as e:
                logger.warning("Fast-path open application (pyautogui) failed: %s", e)
        
        elif yt_query:
            import urllib.parse
            search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(yt_query)}"
            try:
                import webbrowser
                webbrowser.open(search_url)
                fast_path_response = f"Searched YouTube for '{yt_query}' directly (Fast-path)."
                fast_path_tool_calls.append({"name": "open_url_in_browser", "args": {"url": search_url}, "id": str(uuid.uuid4())})
            except Exception as e:
                logger.warning("Fast-path youtube search failed: %s", e)

        elif security_match:
            try:
                import psutil
                import tempfile
                
                warnings = []
                
                # Check for suspicious backdoors (listening on uncommon ports)
                common_ports = {80, 443, 8000, 8080, 3000, 5173, 3306, 5432, 22, 53, 135, 139, 445, 21, 25, 110, 143, 3389, 5000, 8001}
                suspicious_conns = []
                for conn in psutil.net_connections(kind='inet'):
                    if conn.status == 'LISTEN':
                        port = conn.laddr.port
                        if port not in common_ports:
                            try:
                                proc = psutil.Process(conn.pid)
                                name = proc.name()
                                if name.lower() not in ["svchost.exe", "system", "wininit.exe", "spoolsv.exe"]:
                                    suspicious_conns.append(f"Port {port} ({name})")
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
                
                if suspicious_conns:
                    warnings.append("🚨 Possible backdoors detected! Unknown processes listening on uncommon ports: " + ", ".join(suspicious_conns[:5]))
                
                # Check for suspicious files in temp directory recently created
                temp_dir = tempfile.gettempdir()
                suspicious_files = []
                now = time.time()
                for root, dirs, files in os.walk(temp_dir):
                    # Only search top level or 1 level deep to be fast
                    if root != temp_dir and os.path.dirname(root) != temp_dir:
                        continue
                    for f in files:
                        if f.lower().endswith(('.exe', '.bat', '.vbs', '.ps1')):
                            filepath = os.path.join(root, f)
                            try:
                                mtime = os.path.getmtime(filepath)
                                if now - mtime < 86400: # Modified in last 24 hours
                                    suspicious_files.append(f)
                            except Exception:
                                pass
                
                if suspicious_files:
                    warnings.append("🚨 Suspicious executables found in Temp directory: " + ", ".join(suspicious_files[:5]))
                    
                if warnings:
                    fast_path_response = "\n\n".join(warnings) + "\n\nSay 'analyze security deeply' to have the Security Agent investigate these findings."
                else:
                    fast_path_response = "✅ System Security Scan complete. No immediate backdoors or suspicious temp files detected."
            except Exception as e:
                logger.warning("Fast-path security scan failed: %s", e)
                fast_path_response = f"Security scan encountered an error: {str(e)}"
        
        elif type_enter_match or type_only_match:
            import pyautogui
            match_obj = type_enter_match if type_enter_match else type_only_match
            prefix_len = match_obj.end(0) - len(match_obj.group(1))
            text_to_type = spellcheck_target(request_message.strip()[prefix_len:].strip().strip("'").strip('"'))
    
            try:
                return_focus_if_omniagent()
                pyautogui.write(text_to_type, interval=0.01)
        
                if type_enter_match:
                    time.sleep(0.1)
                    pyautogui.press('enter')
                    fast_path_response = f"Typed '{text_to_type}' and pressed Enter directly in your active window (Fast-path)."
                else:
                    fast_path_response = f"Typed '{text_to_type}' directly in your active window (Fast-path)."
            except Exception as e:
                logger.warning("Fast-path typing failed: %s", e)

        if fast_path_response:
            responses.append(fast_path_response)

    if responses:
        return " ".join(responses), fast_path_tool_calls
    return None, []
