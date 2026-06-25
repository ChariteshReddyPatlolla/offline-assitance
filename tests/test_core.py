import pytest
import asyncio
from agent_os.core.models import PlannedTask, ExecutionPlan
from agent_os.core.events import EventBus, EventMessage
from agent_os.core.queues import TaskQueue, Task

def test_models():
    task = PlannedTask(task_id="t1", description="desc", dependencies=["t0"])
    assert task.task_id == "t1"
    assert task.dependencies == ["t0"]
    
    plan = ExecutionPlan(original_goal="goal", tasks=[task])
    assert plan.original_goal == "goal"
    assert len(plan.tasks) == 1

@pytest.mark.asyncio
async def test_event_bus():
    bus = EventBus()
    received = []
    
    async def handler(msg: EventMessage):
        received.append(msg.payload)
        
    bus.subscribe("test_event", handler)
    await bus.publish(EventMessage(event_type="test_event", source="test", payload={"key": "val"}))
    
    assert len(received) == 1
    assert received[0] == {"key": "val"}

@pytest.mark.asyncio
async def test_task_queue():
    queue = TaskQueue()
    task = Task(id="task_1", target_agent="test", payload={})
    
    await queue.enqueue(task)
    assert queue.get_task_status("task_1") == "pending"
    
    dequeued = await queue.dequeue()
    assert dequeued.id == "task_1"
    assert dequeued.status == "running"
    
    queue.mark_completed("task_1", result="success")
    assert queue.get_task_status("task_1") == "completed"
