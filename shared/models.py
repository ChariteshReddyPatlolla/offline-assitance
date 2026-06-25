import datetime
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from shared.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    sessions = relationship("Session", back_populates="user")

class Session(Base):
    __tablename__ = "sessions"
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"))
    title = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Contextual Memory State
    current_app = Column(String, nullable=True)
    current_project = Column(String, nullable=True)
    current_directory = Column(String, nullable=True)
    current_file = Column(String, nullable=True)
    current_terminal = Column(String, nullable=True)
    current_browser_session = Column(String, nullable=True)
    current_browser_tab = Column(String, nullable=True)
    current_workflow = Column(String, nullable=True)
    open_tabs = Column(Text, nullable=True)  # JSON-serialized list of URLs
    last_action = Column(String, nullable=True)
    previous_actions = Column(Text, nullable=True)  # JSON-serialized list of previous actions

    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("sessions.id"))
    role = Column(String) # 'user', 'assistant', 'system', 'tool'
    content = Column(Text)
    
    # Tool Call Support
    tool_calls = Column(Text, nullable=True) # JSON serialized tool calls for AIMessage
    tool_call_id = Column(String, nullable=True) # Tool Call ID for ToolMessage
    name = Column(String, nullable=True) # Tool Name for ToolMessage
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    session = relationship("Session", back_populates="messages")
