from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime


class MessageBase(BaseModel):
    role: str
    content: str


class Message(MessageBase):
    id: str
    session_id: str
    created_at: datetime
    tools_used: Optional[List[str]] = []
    approval_request: Optional[Dict[str, Any]] = None
    checklist_request: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class Session(BaseModel):
    id: str
    user_id: str
    title: Optional[str] = "New Chat"
    created_at: datetime
    updated_at: datetime
    current_app: Optional[str] = None
    current_directory: Optional[str] = None
    current_file: Optional[str] = None
    open_tabs: Optional[str] = None
    last_action: Optional[str] = None

    class Config:
        from_attributes = True


class User(BaseModel):
    id: str
    username: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    user_id: str


class ApproveRequest(BaseModel):
    action_key: str
    session_id: str
    user_id: str
    original_message: str
    approved: bool


class ChecklistSubmitRequest(BaseModel):
    action_key: str
    session_id: str
    user_id: str
    selected_items: List[Dict[str, Any]]
    original_message: str


class ExplainRequest(BaseModel):
    text: str
    question: Optional[str] = None
    document_id: Optional[str] = None

class ExplainResponse(BaseModel):
    explanation: str
