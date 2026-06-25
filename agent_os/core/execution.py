from typing import Dict, List, Set
from enum import Enum
from .dependency import DependencyEngine
from .models import ExecutionPlan, PlannedTask

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"

class DAGExecutionGraph:
    """
    Runtime tracker for the execution plan.
    Manages task states, progress tracking, and parallel task dispatch.
    """
    
    def __init__(self, plan: ExecutionPlan):
        self.engine = DependencyEngine(plan)
        self.statuses: Dict[str, TaskStatus] = {t.task_id: TaskStatus.PENDING for t in plan.tasks}
        # Initialize blocked vs pending
        self._update_statuses()

    def _update_statuses(self):
        """Recalculate which tasks are blocked vs pending based on dependencies."""
        completed = self.get_completed_tasks()
        ready_tasks = self.engine.get_ready_tasks(completed)
        ready_ids = {t.task_id for t in ready_tasks}
        
        for task_id, status in self.statuses.items():
            if status in (TaskStatus.PENDING, TaskStatus.BLOCKED):
                if task_id in ready_ids:
                    self.statuses[task_id] = TaskStatus.PENDING
                else:
                    self.statuses[task_id] = TaskStatus.BLOCKED

    def get_completed_tasks(self) -> Set[str]:
        return {tid for tid, stat in self.statuses.items() if stat == TaskStatus.COMPLETED}

    def get_executable_tasks(self) -> List[PlannedTask]:
        """Get tasks that are ready to run (PENDING status)."""
        self._update_statuses()
        executable = []
        for task_id, status in self.statuses.items():
            if status == TaskStatus.PENDING:
                executable.append(self.engine.tasks[task_id])
        return executable

    def mark_running(self, task_id: str):
        if self.statuses.get(task_id) == TaskStatus.PENDING:
            self.statuses[task_id] = TaskStatus.RUNNING
        else:
            raise ValueError(f"Task {task_id} cannot transition to RUNNING from {self.statuses.get(task_id)}")

    def mark_completed(self, task_id: str):
        if self.statuses.get(task_id) == TaskStatus.RUNNING:
            self.statuses[task_id] = TaskStatus.COMPLETED
            self._update_statuses()
        else:
            raise ValueError(f"Task {task_id} cannot transition to COMPLETED from {self.statuses.get(task_id)}")

    def mark_failed(self, task_id: str):
        if self.statuses.get(task_id) == TaskStatus.RUNNING:
            self.statuses[task_id] = TaskStatus.FAILED
        else:
            raise ValueError(f"Task {task_id} cannot transition to FAILED from {self.statuses.get(task_id)}")

    def is_fully_completed(self) -> bool:
        return all(status == TaskStatus.COMPLETED for status in self.statuses.values())

    def has_failed(self) -> bool:
        return any(status == TaskStatus.FAILED for status in self.statuses.values())
