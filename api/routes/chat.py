import re

# Initialize fast spellchecker for typo tolerance on targets
try:
    from spellchecker import SpellChecker
    fast_spell = SpellChecker()
    # Add common tech terms to prevent false-positive corrections
    fast_spell.word_frequency.load_words(["leetcode", "whatsapp", "vscode", "youtube", "github", "chatgpt", "claude", "gemini", "spotify", "chrome", "edge", "netflix", "facebook", "twitter", "instagram", "tiktok", "amazon", "flipkart"])
    def spellcheck_target(text):
        if not text: return text
        words = text.split()
        corrected = []
        for w in words:
            corr = fast_spell.correction(w)
            # If the spellchecker returns None or we don't want to change it, keep original
            corrected.append(corr if corr else w)
        return " ".join(corrected)
except ImportError:
    # Fallback if pyspellchecker isn't installed
    def spellcheck_target(text):
        return text
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from shared import schemas, models
from shared.database import get_db
from services.agent.graph import app
import os
import json
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from shared.context import active_session_dir, active_session_file

logger = logging.getLogger(__name__)
router = APIRouter()

APPROVAL_PATTERN = re.compile(r"\[NEEDS_APPROVAL:([^\]]+)\]")
CHECKLIST_PATTERN = re.compile(r"\[CHECKLIST_REQUEST:([^\|]+)\|(.*?)\]", re.DOTALL)


def _extract_approval_request(content: str) -> dict | None:
    """Extract approval metadata from tool output embedded in agent response."""
    match = APPROVAL_PATTERN.search(content)
    if match:
        return {"action_key": match.group(1)}
    return None


def _extract_checklist_request(content: str) -> dict | None:
    """Extract checklist metadata from tool output embedded in agent response."""
    match = CHECKLIST_PATTERN.search(content)
    if match:
        try:
            return {
                "action_key": match.group(1).strip(),
                "data": json.loads(match.group(2).strip())
            }
        except Exception as e:
            logger.error("Failed to parse checklist JSON: %s", e)
    return None


@router.post("/", response_model=schemas.Message)
async def chat_endpoint(
    request: schemas.ChatRequest,
    db: Session = Depends(get_db)
):
    # ------------------------------------------------------------------
    # 1. Fetch existing session or create a new one
    # ------------------------------------------------------------------
    session_id = request.session_id
    if not session_id:
        import uuid
        session_id = str(uuid.uuid4())
        logger.info("Generated a new session_id: %s", session_id)

    # Log incoming request session_id
    logger.info("Incoming chat request for session_id: %s", session_id)

    session = (
        db.query(models.Session)
        .filter(models.Session.id == session_id)
        .first()
    )

    if not session:
        # --------------------------------------------------------------
        # Auto-create user if not found
        # --------------------------------------------------------------
        username = f"user_{request.user_id[:8]}"

        # First try by ID
        user = (
            db.query(models.User)
            .filter(models.User.id == request.user_id)
            .first()
        )

        # If no user with this ID, check if username already exists
        if not user:
            user = (
                db.query(models.User)
                .filter(models.User.username == username)
                .first()
            )

        # Create only if neither ID nor username exists
        if not user:
            user = models.User(
                id=request.user_id,
                username=username
            )

            try:
                db.add(user)
                db.commit()
                db.refresh(user)
            except IntegrityError:
                # Another request may have inserted the same username
                db.rollback()
                user = (
                    db.query(models.User)
                    .filter(models.User.username == username)
                    .first()
                )

        # --------------------------------------------------------------
        # Create new chat session
        # --------------------------------------------------------------
        session = models.Session(
            id=session_id,
            user_id=user.id,
            title=request.message[:60]
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    # ------------------------------------------------------------------
    # 2. Save user message
    # ------------------------------------------------------------------
    user_msg = models.Message(
        session_id=session_id,
        role="user",
        content=request.message
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # ------------------------------------------------------------------
    # 3. Build message history for the agent
    # ------------------------------------------------------------------
    past_messages = (
        db.query(models.Message)
        .filter(models.Message.session_id == session_id)
        .order_by(models.Message.created_at)
        .all()
    )

    langchain_messages = []

    # Retrieve global SYSTEM_PROMPT from services.agent.graph
    from services.agent.graph import SYSTEM_PROMPT

    # Start real-time active window tracker if not already running
    from shared import context
    try:
        context.start_window_tracker()
    except Exception as e:
        logger.warning("Could not start active window tracker: %s", str(e))

    real_time_app = context.last_active_app_name
    real_time_window = context.last_active_window_title

    # Update session based on real-time active window if valid
    if real_time_app and real_time_app != "Desktop":
        session.current_app = real_time_app
        if real_time_app == "Notepad" and " - Notepad" in real_time_window:
            file_part = real_time_window.split(" - Notepad")[0]
            if file_part and file_part != "Untitled" and file_part.strip():
                session.current_file = file_part.strip()
        elif real_time_app == "VS Code" and " - Visual Studio Code" in real_time_window:
            parts = real_time_window.split(" - ")
            if len(parts) >= 2:
                session.current_file = parts[0].strip()
        db.commit()

    # Format the current session's active desktop/application context
    context_str = f"""## Active Desktop Context (REAL-TIME STATUS)
- Current Application: {session.current_app or 'None'}
- Current Directory: {session.current_directory or 'None'}
- Current File: {session.current_file or 'None'}
- Open Tabs: {session.open_tabs or '[]'}
- Last Action: {session.last_action or 'None'}
- Active Window Title: {real_time_window}"""

    # Prepend dynamic SystemMessage combining base system prompt + current session context
    full_prompt = SYSTEM_PROMPT.content + "\n\n" + context_str
    langchain_messages.append(SystemMessage(content=full_prompt))

    # Build message history — inject context reminder directly before the last user message
    # so local LLMs (which read recent tokens most strongly) always see the current state.
    context_reminder = (
        f"[SYSTEM CONTEXT — READ THIS BEFORE REPLYING]\n"
        f"Current Directory: {session.current_directory or 'C:\\Users\\patlo\\Desktop'}\n"
        f"Current File: {session.current_file or 'None'}\n"
        f"Current App: {session.current_app or 'None'}\n"
        f"Active Window Title: {real_time_window}\n"
        f"Last Action: {session.last_action or 'None'}\n"
        f"\nRULE: When the user says 'there', 'that folder', 'that file', 'it', or does not specify a path, "
        f"you MUST use the Current Directory and Current File above. Do NOT default to Desktop unless Current Directory is None."
    )

    all_past = list(past_messages)
    # Separate last user message from history
    last_user_raw = all_past[-1] if all_past else None

    for i, msg in enumerate(all_past):
        is_last = (i == len(all_past) - 1)
        if msg.role == "user":
            if is_last:
                # Inject context reminder as a system note right before the final user message
                langchain_messages.append(HumanMessage(content=context_reminder))
            langchain_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            try:
                tool_calls = json.loads(msg.tool_calls) if msg.tool_calls else []
            except Exception:
                tool_calls = []
            langchain_messages.append(AIMessage(content=msg.content or "", tool_calls=tool_calls))
        elif msg.role == "tool":
            from langchain_core.messages import ToolMessage
            langchain_messages.append(ToolMessage(content=msg.content or "", tool_call_id=msg.tool_call_id or "", name=msg.name or ""))

    # ------------------------------------------------------------------
    # 4. Fast-Path Intent Routing & LangGraph Agent
    # ------------------------------------------------------------------
    from shared.context import current_session_id
    import uuid
    
    token_session = current_session_id.set(session_id)
    token = active_session_dir.set(session.current_directory)
    token_file = active_session_file.set(session.current_file)
    
    import re


    import time
    
    clauses = re.split(r'\b(?:and|then)\b', request.message.strip(), flags=re.IGNORECASE)
    
    import difflib
    command_prefixes = [
        "open", "create file", "make file", "search on youtube", "play on youtube",
        "search youtube for", "play youtube for", "search for", "type and search", "type",
        "lock screen", "lock pc", "lock computer", "show desktop", "minimize all",
        "volume up", "volume down", "volume mute", "volume max",
        "take a screenshot", "take screenshot", "screenshot",
        "play", "pause", "next track", "previous track", "skip",
        "go to", "new tab", "close tab", "go back", "back", 
        "open first link", "open second link", "open third link", "open 1st link", "open it",
        "close this", "minimize this", "maximize this", "refresh this", "reload this",
        "click on", "close", "switch to",
        "write a script", "write script", "write code",
        "run the code", "run code", "run script", "run file", "run this", "run it", "run",
        "open downloads", "open documents", "open pictures", "open desktop", "open music",
        "empty recycle bin", "empty the recycle bin"
    ]
    def fix_typos(text):
        words = text.split()
        for i in [3, 2, 1]:
            if len(words) >= i:
                prefix = " ".join(words[:i]).lower()
                if prefix in command_prefixes:
                    return text
                matches = difflib.get_close_matches(prefix, command_prefixes, n=1, cutoff=0.6)
                if matches:
                    return matches[0] + " " + " ".join(words[i:])
        return text

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
            re.match(r"^(play|pause|next track|previous track|skip)$", ml),
            re.match(r"^(go back|back)$", ml),
            re.match(r"^(?:go\s+to|open)\s+([a-z0-9.-]+\.[a-z]{2,})(?:\s.*)?$", ml),
            re.match(r"^(?:open|go\s+to)\s+(.+)\s+(?:website|site|page)$", ml),
            re.match(r"^(new tab|close tab)$", ml),
            re.match(r"^open\s+(?:the\s+)?(first|second|third|1st|2nd|3rd)\s+link$|^open\s+it$", ml),
            re.match(r"^(close|minimize|maximize|refresh|reload)\s+(?:this|current|it)(?:\s+(window|tab|app|application|page))?$", ml),
            re.match(r"^(?:click\s+(?:on\s+)?|go\s+to\s+)(.+)$", ml),
            re.match(r"^close\s+(.+)$", ml),
            re.match(r"^switch\s+to\s+(.+)$", ml),
            re.match(r"^write\s+(?:a|an\s+)?(.+?)\s+(?:script|code|program)(?:\s+(?:in|on|using)\s+(?:vscode|code|visual studio code))?$", ml),
            re.match(r"^run\s+(?:the\s+)?(?:code|script|file|this|it)$", ml),
            re.match(r"^run\s+(.+\.[a-z0-9]+)$", ml),
            re.match(r"^open\s+(downloads|documents|pictures|desktop|music)$", ml),
            re.match(r"^open\s+([a-z])\s+drive$", ml),
            re.match(r"^empty\s+(?:the\s+)?recycle\s+bin$", ml)
        ]):
            all_fast_paths = False
            break

    fast_path_response = None
    fast_path_tool_calls = []
    responses = []
    
    if all_fast_paths and clauses:
        for i, clause in enumerate(clauses):
            if i > 0:
                time.sleep(1.0)
                
            msg_lower = clause.lower()
            request_message = clause # Re-bind for use inside the loop
            
            # Simple regex matches for low latency execution
            open_app_match = re.match(r"^open\s+(.+)$", msg_lower)
            create_file_match = re.match(r"^(?:create|make)\s+file\s+(.+)$", msg_lower)
            yt_match_1 = re.match(r"^(?:search|play)\s+(?:on\s+)?(?:youtube|yt)\s+(?:for\s+)?(.+)$", msg_lower)
            yt_match_2 = re.match(r"^(?:search|play)\s+(.+?)\s+(?:on\s+)?(?:youtube|yt)$", msg_lower)
            type_enter_match = re.match(r"^(?:type and search|search for)\s+(.+)$", msg_lower)
            type_only_match = re.match(r"^type\s+(.+)$", msg_lower)
    
            # System & Power
            lock_match = re.match(r"^lock\s+(?:the\s+)?(?:screen|pc|computer|system)$", msg_lower)
            desktop_match = re.match(r"^(?:show\s+(?:the\s+)?desktop|minimize\s+all)$", msg_lower)
            vol_match = re.match(r"^(?:volume|vol)\s+(up|down|mute|max)$", msg_lower)
            screenshot_match = re.match(r"^(?:take\s+a\s+)?screenshot$", msg_lower)

            # Media Controls
            media_match = re.match(r"^(play|pause|next track|previous track|skip)$", msg_lower)

            # Web Navigation
            back_match = re.match(r"^(go back|back)$", msg_lower)
            go_match = re.match(r"^(?:go\s+to|open)\s+([a-z0-9.-]+\.[a-z]{2,})(?:\s.*)?$", msg_lower)
            website_match = re.match(r"^(?:open|go\s+to)\s+(.+)\s+(?:website|site|page)$", msg_lower)
            tab_match = re.match(r"^(new tab|close tab)$", msg_lower)
            link_match = re.match(r"^open\s+(?:the\s+)?(first|second|third|1st|2nd|3rd)\s+link$", msg_lower)
            this_match = re.match(r"^(close|minimize|maximize|refresh|reload)\s+(?:this|current|it)(?:\s+(window|tab|app|application|page))?$", msg_lower)

            # Application Management
            click_match = re.match(r"^(?:click\s+(?:on\s+)?|go\s+to\s+)(.+)$", msg_lower)
            close_app_match = re.match(r"^close\s+(.+)$", msg_lower)
            switch_app_match = re.match(r"^switch\s+to\s+(.+)$", msg_lower)

            # Execution
            write_macro_match = re.match(r"^write\s+(?:a|an\s+)?(.+?)\s+(?:script|code|program)(?:\s+(?:in|on|using)\s+(?:vscode|code|visual studio code))?$", msg_lower)
            run_code_match = re.match(r"^run\s+(?:the\s+)?(?:code|script|file|this|it)$", msg_lower)
            run_file_match = re.match(r"^run\s+(.+\.[a-z0-9]+)$", msg_lower)

            # File System
            folder_match = re.match(r"^open\s+(downloads|documents|pictures|desktop|music)$", msg_lower)
            drive_match = re.match(r"^open\s+([a-z])\s+drive$", msg_lower)
            recycle_match = re.match(r"^empty\s+(?:the\s+)?recycle\s+bin$", msg_lower)
    
    
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
                action = media_match.group(1)
                try:
                    import pyautogui
                    if action in ["play", "pause"]:
                        pyautogui.press("playpause")
                        fast_path_response = "Toggled media playback (Fast-path)."
                    elif action in ["next track", "skip"]:
                        pyautogui.press("nexttrack")
                        fast_path_response = "Skipped to next track (Fast-path)."
                    elif action == "previous track":
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
                    # Using DuckDuckGo's 'I'm feeling lucky' bang (\) to instantly redirect to the first search result
                    search_url = f"https://duckduckgo.com/?q=%5C{urllib.parse.quote(query + ' website')}"
                    webbrowser.open(search_url)
                    fast_path_response = f"Opening the {query} website (Fast-path)."
                except Exception as e:
                    logger.warning("Fast-path open website failed: %s", e)

            elif tab_match:
                action = tab_match.group(1)
                try:
                    import pyautogui
                    import time
                    # Yield focus back to the underlying window first
                    pyautogui.hotkey("alt", "tab")
                    time.sleep(0.1)

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
                    import time
                    # Yield focus back to the underlying window first
                    pyautogui.hotkey("alt", "tab")
                    time.sleep(0.2)
            
                    presses = 1
                    if link_pos in ["second", "2nd"]: presses = 2
                    elif link_pos in ["third", "3rd"]: presses = 3
            
                    # Using Down arrow to navigate through search results
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
                    import time
                    # Yield focus back to the underlying window first
                    pyautogui.hotkey("alt", "tab")
                    time.sleep(0.2)
                
                    # Simulate Ctrl+F, type text, Esc, Enter to natively click a link by text on screen
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
                    import time
                    # Yield focus back to the underlying window first
                    pyautogui.hotkey("alt", "tab")
                    time.sleep(0.1)
            
                    if action == "close":
                        if target in ["app", "application", "window"]:
                            pyautogui.hotkey("alt", "f4")
                            fast_path_response = "Closed the current window/app (Fast-path)."
                        else:
                            # Default "close this" or "close this tab" to ctrl+w (safer, closes tabs and documents)
                            pyautogui.hotkey("ctrl", "w")
                            fast_path_response = "Closed the current tab/document (Fast-path)."
                    elif action == "minimize":
                        pyautogui.hotkey("win", "down")
                        pyautogui.hotkey("win", "down") # Twice to ensure minimization if maximized
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
                filename = create_file_match.group(1).strip()
                try:
                    if not os.path.isabs(filename):
                        desktop_path = os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop')
                        filepath = os.path.join(desktop_path, filename)
                    else:
                        filepath = os.path.abspath(filename)
                    if not os.path.exists(filepath):
                        with open(filepath, 'w') as f:
                            f.write("")
                    os.startfile(filepath)
                    fast_path_response = f"Created and opened '{filename}' (Fast-path)."
                except Exception as e:
                    logger.warning("Fast-path create file failed: %s", e)

            elif write_macro_match:
                task = write_macro_match.group(1).strip()
                try:
                    from langchain_ollama import ChatOllama
            
                    # Request raw code from LLM
                    fast_llm = ChatOllama(model="llama3.2:latest", temperature=0.1, keep_alive=-1)
                    ai_msg = await fast_llm.ainvoke([
                        HumanMessage(content=f"Write a {task} script/program. Output ONLY the raw code. Do NOT wrap it in markdown block quotes (e.g. no ```python). Do NOT add any explanations or comments outside the code.")
                    ])
                    raw_code = ai_msg.content.strip()
            
                    # Clean up markdown if the LLM hallucinated it
                    if raw_code.startswith("```"):
                        lines = raw_code.split("\n")
                        if len(lines) >= 2:
                            lines = lines[1:] 
                            if lines and lines[-1].startswith("```"):
                                lines = lines[:-1]
                        raw_code = "\n".join(lines).strip()
                
                    # Determine extension
                    ext = ".py" # default
                    t_lower = task.lower()
                    if "javascript" in t_lower or "js" in t_lower or "node" in t_lower: ext = ".js"
                    elif "html" in t_lower: ext = ".html"
                    elif "cpp" in t_lower or "c++" in t_lower: ext = ".cpp"
                    elif "java" in t_lower: ext = ".java"
                    elif "bash" in t_lower or "shell" in t_lower: ext = ".sh"
                    elif "bat" in t_lower: ext = ".bat"
            
                    filename = f"generated_{task.replace(' ', '_').replace('/', '_')[:20]}{ext}"
                    desktop_path = os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop')
                    filepath = os.path.join(desktop_path, filename)
            
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(raw_code)
                
                    # Track this file so we can run it directly if the user says "run it"
                    import shared.context
                    shared.context.last_generated_file = filepath
                
                    # Open in VS Code
                    from services.tools.impl.desktop import open_file_in_vscode_raw
                    open_file_in_vscode_raw(filepath)
            
                    fast_path_response = f"Successfully generated '{task}' code, saved it to {filename}, and opened it in VS Code! Say 'run the code' to execute it."
                except Exception as e:
                    logger.warning("Fast-path write code macro failed: %s", e)
                    fast_path_response = f"Failed to generate code via Macro. Error: {str(e)}"

            elif run_code_match:
                try:
                    import pyautogui
                    import time
                    # Switch back to the previous window (which is VS Code after generating/opening the file)
                    pyautogui.hotkey("alt", "tab")
                    time.sleep(0.5)
                    # Ctrl+F5 is the standard shortcut to "Run Without Debugging" in VS Code
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
                            # Open in a new cmd window so they can see the output
                            subprocess.Popen(f'start cmd /k {cmd}', shell=True)
                            fast_path_run_resp = f"Running {filename} in a new terminal (Fast-path)."
                        elif not fast_path_run_resp:
                            os.startfile(filepath)
                            fast_path_run_resp = f"Executed {filename} (Fast-path)."
                    else:
                        fast_path_run_resp = f"Could not find '{filename}' to run. If you want the AI to write it, specify the instructions."
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
                    # SHEmptyRecycleBinW flags: SHERB_NOCONFIRMATION=1, SHERB_NOPROGRESSUI=2, SHERB_NOSOUND=4
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
        
                # Resolve common aliases for search
                if app_query in ["vscode", "vs code", "code"]:
                    app_query = "visual studio code"
                elif app_query in ["chrome", "google chrome"]:
                    app_query = "chrome"
            
                from services.tools.impl.desktop import search_start_menu_raw
                import shutil
        
                # Verify if the app exists on the machine
                is_installed = False
                if search_start_menu_raw(app_query):
                    is_installed = True
                elif shutil.which(app_query) or shutil.which(f"{app_query}.exe"):
                    is_installed = True
                else:
                    # Check for Windows Store apps (UWP) via registered URI protocol (e.g., WhatsApp, Spotify)
                    try:
                        import winreg
                        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, app_query) as key:
                            is_installed = True
                    except OSError:
                        pass
            
                if is_installed:
                    try:
                        import pyautogui
                        import time
                        # Simulate searching in the start menu
                        pyautogui.press('win')
                        time.sleep(0.5)
                        pyautogui.write(app_name, interval=0.05)
                        time.sleep(0.5)
                        pyautogui.press('enter')
                
                        fast_path_response = f"Searched for and opened {app_name} via Windows Search (Fast-path)."
                        fast_path_tool_calls = [{"name": "open_application", "args": {"app_name": app_name}, "id": str(uuid.uuid4())}]
                    except Exception as e:
                        logger.warning("Fast-path open application (pyautogui) failed: %s", e)
            
            elif yt_query:
                import urllib.parse
                search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(yt_query)}"
                try:
                    import webbrowser
                    webbrowser.open(search_url)
                    fast_path_response = f"Searched YouTube for '{yt_query}' directly (Fast-path)."
                    fast_path_tool_calls = [{"name": "open_url_in_browser", "args": {"url": search_url}, "id": str(uuid.uuid4())}]
                except Exception as e:
                    logger.warning("Fast-path youtube search failed: %s", e)
            
            elif type_enter_match or type_only_match:
                import pyautogui
                import time
                match_obj = type_enter_match if type_enter_match else type_only_match
                prefix_len = match_obj.end(0) - len(match_obj.group(1))
                # Extract exact casing and strip optional quotes
                text_to_type = spellcheck_target(request_message.strip()[prefix_len:].strip().strip("'").strip('"'))
        
                try:
                    # Yield focus to the underlying window first so it doesn't type into the chat UI
                    pyautogui.hotkey("alt", "tab")
                    time.sleep(0.1)
            
                    # Type the text instantly into whatever window/field is currently focused
                    pyautogui.write(text_to_type, interval=0.01)
            
                    if type_enter_match:
                        time.sleep(0.1)
                        pyautogui.press('enter')
                        fast_path_response = f"Typed '{text_to_type}' and pressed Enter directly in your active window (Fast-path)."
                    else:
                        fast_path_response = f"Typed '{text_to_type}' directly in your active window (Fast-path)."
                
                    fast_path_tool_calls = []
                except Exception as e:
                    logger.warning("Fast-path typing failed: %s", e)

            elif create_file_match:
                # Extract filename with original casing from request_message
                # The offset is the length of the matched "create file " or "make file " part.
                prefix_len = create_file_match.end(0) - len(create_file_match.group(1))
                filename = request_message.strip()[prefix_len:].strip()
                from services.tools.file_ops import write_file
                try:
                    write_file.invoke({"filepath": filename, "content": ""})
                    fast_path_response = f"Created file {filename} directly (Fast-path)."
                    fast_path_tool_calls = [{"name": "write_file", "args": {"filepath": filename, "content": ""}, "id": str(uuid.uuid4())}]
                except Exception as e:
                    logger.warning("Fast-path create file failed: %s", e)


                if fast_path_response:
                    responses.append(fast_path_response)
                    fast_path_response = None
                
        if responses:
            fast_path_response = " ".join(responses)

    try:
        if fast_path_response:
            logger.info("Fast-path triggered for message: '%s'", request.message)
            # Simulate a successful LangGraph state response
            final_state = {
                "messages": langchain_messages + [AIMessage(content=fast_path_response, tool_calls=fast_path_tool_calls)]
            }
        else:
            logger.info("Queueing agent task for session %s", session_id)
            import os
            import subprocess
            import redis
            import uuid
            from langchain_core.messages import messages_to_dict
            
            # Create a file in the workspace
            workspace_dir = session.current_directory or r"C:\Users\patlo\Desktop"
            if not os.path.exists(workspace_dir):
                workspace_dir = r"C:\Users\patlo\Desktop"
                
            task_id = str(uuid.uuid4())[:8]
            thought_file = os.path.join(workspace_dir, f"llm_thought_{task_id}.md")
            
            with open(thought_file, "w", encoding="utf-8") as f:
                f.write(f"# The LLM is thinking...\n\nYour query: `{request.message}`\n\nPlease wait, I will paste the output here when ready.")
            
            # Open in VS Code
            try:
                subprocess.Popen(["code", thought_file], shell=True)
            except Exception as e:
                logger.warning("Failed to open VS Code: %s", e)
            
            # Connect to Redis
            try:
                r = redis.Redis(host='localhost', port=6379, db=0)
                task_payload = {
                    "session_id": session_id,
                    "file_path": thought_file,
                    "messages": messages_to_dict(langchain_messages)
                }
                r.rpush("llm_task_queue", json.dumps(task_payload))
                
                # Synthetic fast response
                fast_path_response = f"I've put this task in the background. Check `{os.path.basename(thought_file)}` in VS Code for the output!"
                final_state = {
                    "messages": langchain_messages + [AIMessage(content=fast_path_response)]
                }
            except Exception as e:
                logger.error("Failed to connect to Redis: %s", e)
                # Fallback to synchronous execution if Redis is down
                from fastapi.concurrency import run_in_threadpool
                final_state = await run_in_threadpool(app.invoke, {"messages": langchain_messages})

    except Exception as e:
        logger.exception("Agent error")
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {str(e)}"
        )
    finally:
        active_session_dir.reset(token)
        active_session_file.reset(token_file)
        current_session_id.reset(token_session)

    # ------------------------------------------------------------------
    # 5. Extract final AI response
    # ------------------------------------------------------------------
    agent_response = "I'm sorry, I was unable to generate a response."
    approval_request = None
    checklist_request = None

    for msg in reversed(final_state["messages"]):
        if msg.content and isinstance(msg.content, str) and msg.content.strip():
            temp_approval = _extract_approval_request(msg.content.strip())
            temp_checklist = _extract_checklist_request(msg.content.strip())
            
            if temp_checklist:
                agent_response = msg.content.strip()
                # Clean the response to remove the token
                agent_response = CHECKLIST_PATTERN.sub("", agent_response).strip()
                checklist_request = temp_checklist
                break
            elif temp_approval:
                agent_response = msg.content.strip()
                approval_request = temp_approval
                break
            elif isinstance(msg, AIMessage):
                agent_response = msg.content.strip()
                break

    # ------------------------------------------------------------------
    # 6. Parse and save context state from agent response & tool calls
    # ------------------------------------------------------------------
    # Look for a context_state block in the agent response
    context_match = re.search(r"```(?:context_state|json)?\s*({.*?})\s*```", agent_response, re.DOTALL)
    if context_match:
        try:
            state_data = json.loads(context_match.group(1))
            if "current_app" in state_data:
                session.current_app = state_data["current_app"]
            if "current_directory" in state_data:
                session.current_directory = state_data["current_directory"]
            if "current_file" in state_data:
                session.current_file = state_data["current_file"]
            if "open_tabs" in state_data:
                session.open_tabs = json.dumps(state_data["open_tabs"])
            if "last_action" in state_data:
                session.last_action = state_data["last_action"]
            db.commit()
            logger.info("Successfully updated session context state from agent: %s", state_data)
        except Exception as e:
            logger.warning("Failed to parse context_state JSON: %s", str(e))
        
        # Clean the agent response to strip the context_state block so the user never sees it in the chat UI
        agent_response = re.sub(r"```(?:context_state|json)?\s*({.*?})\s*```", "", agent_response, flags=re.DOTALL).strip()

    logger.debug("Fallback analyzer message types: %s", [(m.__class__.__name__, type(m)) for m in final_state["messages"]])
    # Fallback / Auto-extract context from recent tool calls if present
    try:
        for msg in reversed(final_state["messages"]):
            if msg.__class__.__name__ == "AIMessage" and getattr(msg, "tool_calls", None):
                for tc in msg.tool_calls:
                    args = tc.get("args", {})
                    name = tc.get("name", "")
                    logger.debug("Fallback analyzer checked tool call: name=%s, args=%s", name, args)
                    if name == "write_file" and "filepath" in args:
                        written_path = args["filepath"]
                        session.current_file = written_path
                        session.current_directory = os.path.dirname(written_path)
                        session.last_action = f"Wrote to file {os.path.basename(written_path)}"
                    elif name == "delete_file" and "filepath" in args:
                        session.last_action = f"Deleted file {os.path.basename(args['filepath'])}"
                    elif name == "create_directory" and "path" in args:
                        # Trust the absolute path from the tool args directly — do NOT call
                        # os.path.abspath() here because that uses the API server's cwd (project root)
                        created_path = args["path"]
                        session.current_directory = created_path
                        session.last_action = f"Created directory {os.path.basename(created_path)}"
                    elif name == "open_application" and "app_name" in args:
                        session.current_app = args["app_name"]
                        session.last_action = f"Opened application {args['app_name']}"
                        app_path = args.get("path")
                        if app_path:
                            abs_app_path = os.path.abspath(app_path)
                            if os.path.isdir(abs_app_path) or (not os.path.exists(abs_app_path) and not os.path.basename(abs_app_path).count('.')):
                                session.current_directory = abs_app_path
                            else:
                                session.current_file = abs_app_path
                                session.current_directory = os.path.dirname(abs_app_path)
                    elif name == "close_application" and "app_name" in args:
                        if session.current_app and session.current_app.lower() == args["app_name"].lower():
                            session.current_app = None
                        session.last_action = f"Closed application {args['app_name']}"
                    elif name == "open_url_in_browser" and "url" in args:
                        session.current_app = "Browser"
                        session.last_action = f"Opened URL {args['url']}"
                        # Append to open_tabs
                        try:
                            tabs = json.loads(session.open_tabs) if session.open_tabs else []
                            if args["url"] not in tabs:
                                tabs.append(args["url"])
                                session.open_tabs = json.dumps(tabs)
                        except:
                            pass
                    elif name == "press_hotkey" and "keys" in args:
                        keys = args["keys"].strip().lower()
                        if "alt+f4" in keys:
                            closed_app = session.current_app or "application"
                            session.current_app = None
                            session.current_file = None
                            session.last_action = f"Closed active window ({closed_app})"
                        elif "ctrl+w" in keys:
                            session.last_action = "Closed active browser tab"
                    elif name == "execute_shell_command" and "command" in args:
                        cmd = args["command"].strip()
                        session.last_action = f"Ran shell command: {cmd}"
                        # Check for cd command
                        cd_match = re.match(r"^cd\s+(.+)$", cmd, re.IGNORECASE)
                        if cd_match:
                            session.current_directory = os.path.abspath(cd_match.group(1))
                db.commit()
    except Exception as e:
        logger.warning("Error auto-extracting context from tool calls: %s", str(e))

    # ------------------------------------------------------------------
    # 7. Save all new assistant and tool messages
    # ------------------------------------------------------------------
    new_messages = final_state["messages"][len(langchain_messages):]
    assistant_msg = None
    
    for msg in new_messages:
        if isinstance(msg, AIMessage):
            tool_calls_json = json.dumps(msg.tool_calls) if getattr(msg, "tool_calls", None) else None
            # If it's the very last message or has content, treat it as the final response message
            db_msg = models.Message(
                session_id=session_id,
                role="assistant",
                content=msg.content if isinstance(msg.content, str) else str(msg.content or ""),
                tool_calls=tool_calls_json
            )
            db.add(db_msg)
            db.commit()
            db.refresh(db_msg)
            assistant_msg = db_msg
        elif msg.__class__.__name__ == "ToolMessage":
            db_msg = models.Message(
                session_id=session_id,
                role="tool",
                content=msg.content if isinstance(msg.content, str) else str(msg.content or ""),
                tool_call_id=getattr(msg, "tool_call_id", ""),
                name=getattr(msg, "name", "")
            )
            db.add(db_msg)
            db.commit()

    if not assistant_msg:
        # Fallback if no AIMessage was added
        assistant_msg = models.Message(
            session_id=session_id,
            role="assistant",
            content=agent_response
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)
    else:
        # Ensure the final response content is accurate for the API return
        assistant_msg.content = agent_response
        db.commit()
        db.refresh(assistant_msg)

    # ------------------------------------------------------------------
    # 7. Build API response
    # ------------------------------------------------------------------
    result = schemas.Message.model_validate(assistant_msg)

    # Attach approval info for frontend Yes/No buttons
    if approval_request:
        approval_request["session_id"] = session_id
        approval_request["original_message"] = request.message
        result.approval_request = approval_request

    if checklist_request:
        checklist_request["session_id"] = session_id
        checklist_request["original_message"] = request.message
        result.checklist_request = checklist_request

    return result


@router.post("/submit_checklist", response_model=schemas.Message)
async def submit_checklist_endpoint(
    req: schemas.ChecklistSubmitRequest,
    db: Session = Depends(get_db)
):
    """
    Handles when a user hits 'Submit Selected' on a checklist UI.
    It injects a system message indicating the selections and triggers the agent again.
    """
    session = db.query(models.Session).filter(models.Session.id == req.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    selected_str = json.dumps(req.selected_items, indent=2)
    # The message we simulate the user sending
    injected_message = (
        f"I have selected the following items from the checklist for action '{req.action_key}':\n"
        f"{selected_str}\n\n"
        f"Please proceed with the appropriate actions for these selected items."
    )

    # Re-use the existing chat endpoint flow by calling it recursively or duplicating logic
    # The easiest is to just dispatch a new ChatRequest
    new_req = schemas.ChatRequest(
        session_id=req.session_id,
        user_id=req.user_id,
        message=injected_message
    )
    return await chat_endpoint(new_req, db)


@router.post("/stop/{session_id}")
async def stop_chat_endpoint(session_id: str):
    """
    Adds the session_id to the cancellation list.
    The LangGraph agent checks this set in its node transitions and breaks if present.
    """
    from shared.context import cancel_requests
    logger.info("Cancellation requested for session_id: %s", session_id)
    cancel_requests.add(session_id)
    return {"status": "stopping", "session_id": session_id}