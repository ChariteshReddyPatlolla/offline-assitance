"""
Session management API routes.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from typing import List
from shared import schemas, models
from shared.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{user_id}", response_model=List[schemas.Session])
def get_user_sessions(user_id: str, db: DBSession = Depends(get_db)):
    """Get all sessions for a user, ordered by most recent first."""
    sessions = (
        db.query(models.Session)
        .filter(models.Session.user_id == user_id)
        .order_by(models.Session.updated_at.desc())
        .all()
    )
    return sessions


@router.get("/{session_id}/messages", response_model=List[schemas.Message])
def get_session_messages(session_id: str, db: DBSession = Depends(get_db)):
    """Get all messages for a session."""
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = (
        db.query(models.Message)
        .filter(models.Message.session_id == session_id)
        .order_by(models.Message.created_at)
        .all()
    )
    return messages


@router.delete("/{session_id}")
def delete_session(session_id: str, db: DBSession = Depends(get_db)):
    """Delete a session and all its messages."""
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    logger.info("Deleted session: %s", session_id)
    return {"status": "deleted", "session_id": session_id}


@router.patch("/{session_id}/title")
def update_session_title(session_id: str, title: str, db: DBSession = Depends(get_db)):
    """Update a session title."""
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.title = title
    db.commit()
    return {"status": "updated", "title": title}
