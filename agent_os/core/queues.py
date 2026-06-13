import asyncio
from typing import Any, Dict
from pydantic import BaseModel, Field

class Task(BaseModel):
    """Represents an execution task in the queue."""
    id: str
    target_agent: str
    payload: Dict[str, Any]
    status: str = Field(default="pending")  # pending, running, completed, failed
    result: Any = None
    error: str = None

class TaskQueue:
    """
    Asynchronous task queue for execution tracking and message passing.
    """
    def __init__(self):
        self._queue: asyncio.Queue[Task] = asyncio.Queue()
        self._tasks: Dict[str, Task] = {}

    async def enqueue(self, task: Task):
        """Add a task to the queue."""
        self._tasks[task.id] = task
        await self._queue.put(task)

    async def dequeue(self) -> Task:
        """Get the next task from the queue."""
        task = await self._queue.get()
        task.status = "running"
        return task

    def mark_completed(self, task_id: str, result: Any):
        """Mark a task as completed."""
        if task_id in self._tasks:
            self._tasks[task_id].status = "completed"
            self._tasks[task_id].result = result
            self._queue.task_done()

    def mark_failed(self, task_id: str, error: str):
        """Mark a task as failed."""
        if task_id in self._tasks:
            self._tasks[task_id].status = "failed"
            self._tasks[task_id].error = error
            self._queue.task_done()
            
    def get_task_status(self, task_id: str) -> str:
        if task_id in self._tasks:
            return self._tasks[task_id].status
        return "unknown"
