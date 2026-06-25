from typing import Dict, List, Set
from .models import ExecutionPlan, PlannedTask

class DependencyEngine:
    """
    Builds and manages a Directed Acyclic Graph (DAG) for tasks.
    Supports cycle detection and topological sorting.
    """
    
    def __init__(self, plan: ExecutionPlan):
        self.plan = plan
        self.tasks: Dict[str, PlannedTask] = {t.task_id: t for t in plan.tasks}
        self.validate_dag()

    def validate_dag(self):
        """
        Validates that dependencies exist and that there are no cycles.
        """
        for task in self.tasks.values():
            for dep in task.dependencies:
                if dep not in self.tasks:
                    raise ValueError(f"Task '{task.task_id}' depends on unknown task '{dep}'.")
                    
        # Cycle detection using DFS
        visited = set()
        path = set()

        def dfs(node_id: str):
            if node_id in path:
                raise ValueError(f"Cycle detected involving task '{node_id}'")
            if node_id in visited:
                return
                
            visited.add(node_id)
            path.add(node_id)
            
            for dep in self.tasks[node_id].dependencies:
                dfs(dep)
                
            path.remove(node_id)

        for task_id in self.tasks:
            dfs(task_id)

    def get_ready_tasks(self, completed_tasks: Set[str]) -> List[PlannedTask]:
        """
        Returns a list of tasks whose dependencies are fully met by the completed_tasks set.
        """
        ready = []
        for task in self.tasks.values():
            if task.task_id in completed_tasks:
                continue
            
            # Check if all dependencies are in completed_tasks
            can_run = all(dep in completed_tasks for dep in task.dependencies)
            if can_run:
                ready.append(task)
                
        return ready
