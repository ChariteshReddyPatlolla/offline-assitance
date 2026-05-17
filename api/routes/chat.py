import re
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
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
async def chat_endpoint(request: schemas.ChatRequest, db: Session = Depends(get_db)):
    # 1. Fetch or create session
    session_id = request.session_id
    if session_id:
        session = db.query(models.Session).filter(models.Session.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        # Auto-create user if not found
        user = db.query(models.User).filter(models.User.id == request.user_id).first()
        if not user:
            user = models.User(id=request.user_id, username=f"user_{request.user_id[:8]}")
            db.add(user)
            db.commit()
            db.refresh(user)

        session = models.Session(user_id=request.user_id, title=request.message[:60])
        db.add(session)
        db.commit()
        db.refresh(session)
        session_id = session.id

    # 2. Save user message
    user_msg = models.Message(session_id=session_id, role="user", content=request.message)
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # 3. Build message history for the agent
    past_messages = (
        db.query(models.Message)
        .filter(models.Message.session_id == session_id)
        .order_by(models.Message.created_at)
        .all()
    )

    langchain_messages = []
    for msg in past_messages:
        if msg.role == "user":
            langchain_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            langchain_messages.append(AIMessage(content=msg.content))

    # 4. Run LangGraph agent
    try:
        logger.info("Running agent for session %s: '%s'", session_id, request.message[:80])
        final_state = app.invoke({"messages": langchain_messages})
    except Exception as e:
        logger.error("Agent error: %s", e)
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    # 5. Extract final text reply
    agent_response = "I'm sorry, I was unable to generate a response."
    approval_request = None

    for msg in reversed(final_state["messages"]):
        if isinstance(msg, AIMessage) and msg.content and isinstance(msg.content, str) and msg.content.strip():
            agent_response = msg.content.strip()
            # Check if this response contains an approval request
            approval_request = _extract_approval_request(agent_response)
            break

    # 6. Save agent response to DB
    assistant_msg = models.Message(
        session_id=session_id,
        role="assistant",
        content=agent_response
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    # 7. Build response — include session_id and approval info
    result = schemas.Message.model_validate(assistant_msg)

    # Attach approval request info if present (for frontend to render Yes/No buttons)
    if approval_request:
        approval_request["session_id"] = session_id
        approval_request["original_message"] = request.message
        result.approval_request = approval_request

    return result
