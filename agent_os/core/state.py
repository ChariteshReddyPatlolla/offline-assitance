from typing import Annotated, Any, Dict, List, Sequence, TypedDict
import operator

class AgentState(TypedDict):
    """
    Enhanced shared state for LangGraph nodes.
    Includes execution tracking, tasks, and coordinator state.
    """
    # Standard conversation history
    messages: Annotated[Sequence[Dict[str, Any]], operator.add]
    
    # State flags
    current_agent: str
    next_node: str
    
    # Task Queue / Execution Tracking
    pending_tasks: Annotated[List[Dict[str, Any]], operator.add]
    completed_tasks: Annotated[List[Dict[str, Any]], operator.add]
    
    # Global context & Memory
    context: Dict[str, Any]
    requirements: Dict[str, Any]
    architecture: Dict[str, Any]
    error: str | None
