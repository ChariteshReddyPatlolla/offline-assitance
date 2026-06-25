import pytest
import asyncio
from agent_os.core.executor import ExecutorEngine
from agent_os.core.models import PlannedTask, ValidationCriteria, RollbackAction
from agent_os.core.registry import ToolRegistry
from agent_os.core.permissions import PermissionManager
import os

@pytest.fixture
def tool_registry():
    registry = ToolRegistry()
    registry.register("create_file", lambda path: open(path, 'w').close())
    registry.register("delete_file", lambda path: os.remove(path) if os.path.exists(path) else None)
    registry.register("file_exists", lambda path: os.path.exists(path))
    registry.register("fail_tool", lambda: (_ for _ in ()).throw(Exception("Force Fail")))
    return registry

@pytest.mark.asyncio
async def test_executor_engine_success(tool_registry):
    permission_manager = PermissionManager()
    engine = ExecutorEngine(tool_registry, permission_manager)
    task = PlannedTask(
        task_id="t1",
        description="Create test file",
        tool_name="create_file",
        tool_parameters={"path": "test_exec.txt"},
        validation=ValidationCriteria(check_type="file_exists", parameters={"path": "test_exec.txt"}),
        rollback=RollbackAction(tool_name="delete_file", parameters={"path": "test_exec.txt"}),
        max_retries=1
    )
    
    success = await engine.execute_task(task)
    assert success is True
    assert os.path.exists("test_exec.txt")
    assert len(engine.rollback_stack) == 1
    
    # Clean up manually
    os.remove("test_exec.txt")

@pytest.mark.asyncio
async def test_executor_engine_fail_and_rollback(tool_registry):
    permission_manager = PermissionManager()
    engine = ExecutorEngine(tool_registry, permission_manager)
    # Add a mock successful action to the rollback stack
    engine.rollback_stack.append(RollbackAction(tool_name="create_file", parameters={"path": "rollback_test.txt"}))
    
    # Task that will fail
    task = PlannedTask(
        task_id="t_fail",
        description="Will fail",
        tool_name="fail_tool",
        tool_parameters={},
        max_retries=1
    )
    
    success = await engine.execute_task(task)
    assert success is False
    
    # Rollback should pop and execute create_file
    await engine.rollback()
    assert os.path.exists("rollback_test.txt")
    
    # Clean up
    os.remove("rollback_test.txt")
