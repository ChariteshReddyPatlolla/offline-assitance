import pytest
from agent_os.core.models import PlannedTask, ExecutionPlan
from agent_os.core.dependency import DependencyEngine
from agent_os.core.execution import DAGExecutionGraph, TaskStatus

def get_mock_plan():
    return ExecutionPlan(
        original_goal="Test",
        tasks=[
            PlannedTask(task_id="A", description="A", dependencies=[]),
            PlannedTask(task_id="B", description="B", dependencies=["A"]),
            PlannedTask(task_id="C", description="C", dependencies=["A"]),
            PlannedTask(task_id="D", description="D", dependencies=["B", "C"]),
        ]
    )

def test_dependency_engine_valid():
    plan = get_mock_plan()
    engine = DependencyEngine(plan)
    assert "A" in engine.tasks

def test_dependency_engine_cycle():
    plan = ExecutionPlan(
        original_goal="Cycle",
        tasks=[
            PlannedTask(task_id="A", description="A", dependencies=["B"]),
            PlannedTask(task_id="B", description="B", dependencies=["A"]),
        ]
    )
    with pytest.raises(ValueError, match="Cycle"):
        DependencyEngine(plan)

def test_dag_execution_graph():
    plan = get_mock_plan()
    graph = DAGExecutionGraph(plan)
    
    # A should be ready
    exec_tasks = graph.get_executable_tasks()
    assert len(exec_tasks) == 1
    assert exec_tasks[0].task_id == "A"
    
    graph.mark_running("A")
    graph.mark_completed("A")
    
    # B and C should now be ready
    exec_tasks = graph.get_executable_tasks()
    assert len(exec_tasks) == 2
    ids = {t.task_id for t in exec_tasks}
    assert "B" in ids and "C" in ids
    
    # Run B
    graph.mark_running("B")
    graph.mark_completed("B")
    
    # D shouldn't be ready yet (C is pending)
    exec_tasks = graph.get_executable_tasks()
    assert len(exec_tasks) == 1
    assert exec_tasks[0].task_id == "C"
    
    # Run C
    graph.mark_running("C")
    graph.mark_completed("C")
    
    # Now D is ready
    exec_tasks = graph.get_executable_tasks()
    assert len(exec_tasks) == 1
    assert exec_tasks[0].task_id == "D"
    
    graph.mark_running("D")
    graph.mark_completed("D")
    
    assert graph.is_fully_completed()
