from typing import Annotated, TypedDict, Sequence, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    """The state of the OmniAgent LangGraph agent."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    pending_tool_call: Optional[dict]
    approval_granted: bool
    approval_request: Optional[dict]  # Populated when a tool needs approval
    is_chat_mode: bool  # Flag indicating whether to skip tools/RAG for lightweight queries
