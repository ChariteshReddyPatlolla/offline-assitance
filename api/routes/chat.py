import re
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from shared import schemas, models
from shared.database import get_db
from services.agent.graph import app
from langchain_core.messages import HumanMessage, AIMessage

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

    if session_id:
        session = (
            db.query(models.Session)
            .filter(models.Session.id == session_id)
            .first()
        )

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

    else:
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
            user_id=user.id,
            title=request.message[:60]
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        session_id = session.id

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
    # 4. Run LangGraph agent
    # ------------------------------------------------------------------
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
    # 6. Save assistant response
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