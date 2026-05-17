"""
Approval API routes — list pending approvals and accept/deny them in-chat.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from shared import schemas, models
from shared.database import get_db
from services.tools.approval_store import grant_approval, deny_approval, get_all_pending, get_pending_for_session
from langchain_core.messages import HumanMessage, AIMessage

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/pending")
def get_pending_approvals():
    """Get all currently pending approval requests."""
    return {"pending": get_all_pending()}


@router.get("/pending/{session_id}")
def get_pending_for_session_route(session_id: str):
    """Get pending approvals for a specific session."""
    return {"pending": get_pending_for_session(session_id)}


@router.post("/decide")
async def decide_approval(request: schemas.ApproveRequest, db: Session = Depends(get_db)):
    """
    Approve or deny an action, then re-run the agent with the original message.
    If approved: grants the action, re-invokes agent so it executes.
    If denied: cancels the action, notifies agent.
    """
    from services.agent.graph import app as agent_app

    action_key = request.action_key

    if request.approved:
        grant_approval(action_key)
        logger.info("User APPROVED action: %s", action_key)
        decision_note = f"[USER_APPROVED:{action_key}] The user approved this action. Please proceed and execute it now."
    else:
        deny_approval(action_key)
        logger.info("User DENIED action: %s", action_key)
        decision_note = f"[USER_DENIED:{action_key}] The user denied this action. Acknowledge and do NOT execute it."

    # Fetch session message history
    session = db.query(models.Session).filter(models.Session.id == request.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    past_messages = (
        db.query(models.Message)
        .filter(models.Message.session_id == request.session_id)
        .order_by(models.Message.created_at)
        .all()
    )

    langchain_messages = []
    for msg in past_messages:
        if msg.role == "user":
            langchain_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            langchain_messages.append(AIMessage(content=msg.content))

    # Append the approval decision as a system note
    langchain_messages.append(HumanMessage(content=decision_note))

    try:
        final_state = agent_app.invoke({"messages": langchain_messages})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error after approval: {str(e)}")

    # Extract agent response
    agent_response = "Action processed." if request.approved else "Action cancelled as requested."
    for msg in reversed(final_state["messages"]):
        if isinstance(msg, AIMessage) and msg.content and isinstance(msg.content, str) and msg.content.strip():
            agent_response = msg.content.strip()
            break

    # Save response to DB
    assistant_msg = models.Message(
        session_id=request.session_id,
        role="assistant",
        content=agent_response
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return schemas.Message.model_validate(assistant_msg)
