import re
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
from shared.context import active_session_dir

logger = logging.getLogger(__name__)
router = APIRouter()

# Regex to detect approval request tokens from the agent
APPROVAL_PATTERN = re.compile(r"\[NEEDS_APPROVAL:([^\]]+)\]")


def _extract_approval_request(content: str) -> dict | None:
    """Extract approval metadata from tool output embedded in agent response."""
    match = APPROVAL_PATTERN.search(content)
    if match:
        return {"action_key": match.group(1)}
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

    # Format the current session's active desktop/application context
    context_str = f"""## Active Desktop Context (REAL-TIME STATUS)
- Current Application: {session.current_app or 'None'}
- Current Directory: {session.current_directory or 'None'}
- Current File: {session.current_file or 'None'}
- Open Tabs: {session.open_tabs or '[]'}
- Last Action: {session.last_action or 'None'}"""

    # Prepend dynamic SystemMessage combining base system prompt + current session context
    full_prompt = SYSTEM_PROMPT.content + "\n\n" + context_str
    langchain_messages.append(SystemMessage(content=full_prompt))

    for msg in past_messages:
        if msg.role == "user":
            langchain_messages.append(
                HumanMessage(content=msg.content)
            )
        elif msg.role == "assistant":
            langchain_messages.append(
                AIMessage(content=msg.content)
            )

    # ------------------------------------------------------------------
    # 4. Run LangGraph agent (in the request-scoped context of the active session's directory)
    # ------------------------------------------------------------------
    token = active_session_dir.set(session.current_directory)
    try:
        logger.info(
            "Running agent for session %s: '%s'",
            session_id,
            request.message[:80]
        )
        final_state = app.invoke({"messages": langchain_messages})

    except Exception as e:
        logger.exception("Agent error")
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {str(e)}"
        )
    finally:
        active_session_dir.reset(token)

    # ------------------------------------------------------------------
    # 5. Extract final AI response
    # ------------------------------------------------------------------
    agent_response = "I'm sorry, I was unable to generate a response."
    approval_request = None

    for msg in reversed(final_state["messages"]):
        if (
            isinstance(msg, AIMessage)
            and isinstance(msg.content, str)
            and msg.content.strip()
        ):
            agent_response = msg.content.strip()

            # Detect approval token
            approval_request = _extract_approval_request(agent_response)
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
                        session.current_file = os.path.abspath(args["filepath"])
                        session.current_directory = os.path.dirname(session.current_file)
                        session.last_action = f"Wrote to file {os.path.basename(session.current_file)}"
                    elif name == "delete_file" and "filepath" in args:
                        session.last_action = f"Deleted file {os.path.basename(args['filepath'])}"
                    elif name == "open_application" and "app_name" in args:
                        session.current_app = args["app_name"]
                        session.last_action = f"Opened application {args['app_name']}"
                    elif name == "close_application" and "app_name" in args:
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
    # 7. Save assistant response
    # ------------------------------------------------------------------
    assistant_msg = models.Message(
        session_id=session_id,
        role="assistant",
        content=agent_response
    )
    db.add(assistant_msg)
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

    return result