import re

# Spellchecking and typo tolerance for fast-paths have been moved to services/fast_path.py
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
    import time
    t_request_start = time.perf_counter()
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
            user_id=request.user_id,
            title="New Chat"
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    # ------------------------------------------------------------------
    # 2. Append the new user message to the DB
    # ------------------------------------------------------------------
    import uuid
    user_msg_id = str(uuid.uuid4())
    user_msg = models.Message(
        id=user_msg_id,
        session_id=session_id,
        role="user",
        content=request.message,
        tool_calls=None
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

    # Build message history — inject context reminder directly before the last user message
    # so local LLMs (which read recent tokens most strongly) always see the current state.
    context_reminder = (
        f"[SYSTEM CONTEXT — READ THIS BEFORE REPLYING]\n"
        f"Current Directory: {session.current_directory or 'C:\\Users\\patlo\\Desktop'}\n"
        f"Current File: {session.current_file or 'None'}\n"
        f"Current App: {session.current_app or 'None'}\n"
    )

    for i, msg in enumerate(past_messages):
        if msg.role == "user":
            if i == len(past_messages) - 1:
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
    
    clauses = re.split(r'\b(?:and|then)\b', request.message.strip(), flags=re.IGNORECASE)
    
    from services.fast_path import process_fast_path_commands
    fast_path_response, fast_path_tool_calls = process_fast_path_commands(clauses)

    try:
        if fast_path_response:
            logger.info("Fast-path triggered for message: '%s'", request.message)
            # Simulate a successful LangGraph state response
            final_state = {
                "messages": langchain_messages + [AIMessage(content=fast_path_response, tool_calls=fast_path_tool_calls)]
            }
        else:
            msg_lower = request.message.lower().strip()
            
            # --- INTENT ROUTER (Phase 2) ---
            import time
            from shared.benchmark_logger import log_metric
            t_router_start = time.perf_counter()
            word_count = len(msg_lower.split())
            is_chat_mode = False
            
            chat_prefixes = ["hi", "hello", "hey", "thanks", "ok", "how are you", "what is", "explain", "tell me"]
            if word_count < 3 or any(msg_lower.startswith(p) for p in chat_prefixes):
                # Exception: if it's a known action command that fell through fast-path, don't treat as chat
                action_keywords = ["open ", "search ", "create ", "write ", "run ", "play ", "send ", "read ", "delete "]
                if not any(msg_lower.startswith(ak) for ak in action_keywords):
                    is_chat_mode = True
                    logger.info("Intent Router: Routed to Chat/Knowledge Mode (Mode B)")
            
            if not is_chat_mode:
                logger.info("Intent Router: Routed to Action Mode (Mode C)")

            t_router_end = time.perf_counter()
            log_metric(session_id, "RouterTime", {"duration": t_router_end - t_router_start, "mode": "Chat" if is_chat_mode else "Action"})


            # Determine if this is a conversational request or a code generation request
            should_background = False
            if any(msg_lower.startswith(p) for p in ["ok do it", "do it", "write ", "create ", "generate ", "code this", "build "]):
                should_background = True
            elif "write" in msg_lower and "code" in msg_lower:
                should_background = True
                
            if should_background:
                logger.info("Queueing agent task for session %s", session_id)
                import ctypes
                import time
                import redis
                import pyautogui
                import uuid
                from langchain_core.messages import messages_to_dict
                from services.fast_path import return_focus_if_omniagent
                
                # Switch back to the IDE if OmniAgent is focused
                return_focus_if_omniagent()
                time.sleep(0.1) # Wait for focus
                
                # Capture the current active window handle and title
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                active_title = buff.value
                
                # Type thinking indicator
                pyautogui.typewrite("// Model is thinking...\n")
                
                # Connect to Redis
                try:
                    r = redis.Redis(host='localhost', port=6379, db=0, protocol=2)
                    task_payload = {
                        "session_id": session_id,
                        "target_hwnd": hwnd,
                        "target_title": active_title,
                        "messages": messages_to_dict(langchain_messages)
                    }
                    r.rpush("llm_task_queue", json.dumps(task_payload))
                    
                    # Synthetic fast response
                    fast_path_response = f"Done sir. I am writing the code in {active_title or 'your editor'} in the background. I will notify you when it's done."
                    final_state = {
                        "messages": langchain_messages + [AIMessage(content=fast_path_response)]
                    }
                except Exception as e:
                    logger.error("Failed to connect to Redis: %s", e)
                    # Fallback to synchronous execution if Redis is down
                    from fastapi.concurrency import run_in_threadpool
                    final_state = await run_in_threadpool(app.invoke, {"messages": langchain_messages, "is_chat_mode": is_chat_mode})
            
            if not should_background:
                logger.info("Executing normal conversational request synchronously for session %s", session_id)
                from fastapi.concurrency import run_in_threadpool
                final_state = await run_in_threadpool(
                    app.invoke,
                    {
                        "messages": langchain_messages,
                        "is_chat_mode": is_chat_mode,
                        "session_id": session_id
                    },
                    config={"configurable": {"thread_id": session_id}}
                )
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

    # Automatically save this interaction to the RAG session context window
    try:
        import threading
        from services.agent.memory import add_session_context
        def save_context_bg():
            try:
                add_session_context(session_id, f"User asked: {request.message}. Action taken: {agent_response}")
            except Exception as e:
                logger.warning(f"Failed to save session context in background: {e}")
        
        threading.Thread(target=save_context_bg, daemon=True).start()
    except Exception as e:
        logger.warning(f"Failed to launch session context thread: {e}")

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

    # Speak the response using pyttsx3, blocking the API return so continuousMode waits
    if agent_response and not checklist_request and not approval_request:
        def speak_text(text: str):
            import pyttsx3
            import pythoncom
            import re
            try:
                pythoncom.CoInitialize()
                engine = pyttsx3.init()
                
                # Simplify fast-path responses for speech
                clean_text = re.sub(r'\(Fast-path\)', '', text, flags=re.IGNORECASE)
                
                if "Searched for and attempted to open" in clean_text:
                    clean_text = "Done sir. I am opening it."
                elif "Switched to" in clean_text:
                    clean_text = "Done sir."
                elif "Typed" in clean_text and "directly in your active window" in clean_text:
                    clean_text = "Done sir. I have typed it."
                elif "I've put this task in the background" in clean_text or "Done sir. I am writing the code" in clean_text:
                    clean_text = "Done sir. I am working on it in the background."
                else:
                    # Remove URLs
                    clean_text = re.sub(r'https?://\S+', '', clean_text)
                    # Don't speak long responses (e.g. research or long text). Just speak the first sentence.
                    if "Source Links" in text or len(text.split()) > 40:
                        sentences = [s.strip() for s in re.split(r'[.!?\n]+', clean_text) if s.strip() and not s.strip().startswith('*')]
                        if sentences:
                            clean_text = sentences[0]
                        else:
                            clean_text = "Here is the information."
                
                # Remove emojis and markdown formatting
                clean_text = re.sub(r'[^a-zA-Z0-9.,!?\' ]', '', clean_text).strip()
                
                if clean_text:
                    engine.say(clean_text)
                    engine.runAndWait()
            except Exception as e:
                logger.error("TTS error: %s", e)
            finally:
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass

        # Run TTS in a background thread so the API returns immediately and UI updates fast
        import threading
        threading.Thread(target=speak_text, args=(agent_response,), daemon=True).start()

    t_request_end = time.perf_counter()
    from shared.benchmark_logger import log_metric
    log_metric(session_id, "TotalRequestTime", {"duration": t_request_end - t_request_start})
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