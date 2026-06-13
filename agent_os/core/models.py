from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field

class ValidationCriteria(BaseModel):
    """Defines what must be true for a task to be considered successful."""
    check_type: str = Field(..., description="E.g., 'file_exists', 'process_running', 'regex_match'")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the check.")

class RollbackAction(BaseModel):
    """Defines the inverse action to undo a task."""
    tool_name: str
    parameters: Dict[str, Any]

class PlannedTask(BaseModel):
    """
    Represents a single decomposed step in an execution plan.
    """
    status: Literal["pending", "in_progress", "completed", "failed", "blocked"] = "pending"
    result: Optional[str] = None
    retry_count: int = 0
    failure_reason: Optional[str] = None
    recovery_attempts: List[str] = Field(default_factory=list)
    confidence_score: Optional[float] = None
    task_id: str = Field(..., description="Unique identifier for this task (e.g., 'task_1').")
    description: str = Field(..., description="Detailed description of what needs to be done.")
    required_capabilities: List[str] = Field(default_factory=list, description="Capabilities required to execute this task.")
    dependencies: List[str] = Field(default_factory=list, description="List of task_ids that must complete before this task can start.")
    
    # Execution specifics
    tool_name: str = Field(default="unknown", description="Name of the tool to execute.")
    tool_parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the tool.")
    validation: Optional[ValidationCriteria] = None
    rollback: Optional[RollbackAction] = None
    max_retries: int = Field(default=3, description="Maximum number of retries before failing.")

class ExecutionPlan(BaseModel):
    """
    The full execution plan composed of multiple tasks.
    """
    original_goal: str = Field(..., description="The user's original goal.")
    tasks: List[PlannedTask] = Field(..., description="List of all decomposed tasks.")
    dag: Dict[str, List[str]] = Field(default_factory=dict, description="Adjacency list representing the dependency DAG. task_id -> list of dependent task_ids")
    milestones: List[str] = Field(default_factory=list, description="List of major milestones mapped to this plan.")
    parallelizable_tasks: List[List[str]] = Field(default_factory=list, description="List of task groups that can be executed in parallel.")
