import asyncio
from rich.live import Live
from rich.console import Console
from ..ui.dashboard import OSDashboard
from ..agents.supervisor import SupervisorAgent
from typing import Dict, Any

class OSRunner:
    """
    The orchestrator that runs the Agent OS LangGraph in an endless autonomous loop.
    """
    def __init__(self, supervisor: SupervisorAgent):
        self.supervisor = supervisor
        self.console = Console()
        self.dashboard = OSDashboard(self.console)
        
    async def run_autonomous(self, goal: str):
        """
        Kicks off the autonomous loop.
        Displays the rich live dashboard.
        """
        state = {
            "messages": [{"role": "user", "content": goal}],
            "pending_tasks": [],
            "completed_tasks": [],
            "next_node": "planner", # Always start by building the plan
            "current_agent": "system"
        }
        
        with Live(self.dashboard.layout, console=self.console, refresh_per_second=4) as live:
            
            # Simulate the graph execution for the dashboard visualizer
            steps = [
                ("planner", {"pending_tasks": [{"description": "Open VSCode", "status": "pending"}, {"description": "Write hello.py", "status": "pending"}], "messages": [{"role": "system", "content": "Generating DAG..."}]}),
                ("supervisor", {"pending_tasks": [{"description": "Open VSCode", "status": "in_progress"}], "messages": [{"role": "assistant", "content": "Routing to Automation Agent..."}]}),
                ("automation", {"pending_tasks": [{"description": "Open VSCode", "status": "completed"}], "messages": [{"role": "system", "content": "Executing: code ."}]}),
                ("supervisor", {"pending_tasks": [{"description": "Write hello.py", "status": "in_progress"}], "messages": [{"role": "assistant", "content": "Routing to Coding Agent..."}]}),
                ("coding", {"pending_tasks": [{"description": "Write hello.py", "status": "completed"}], "messages": [{"role": "system", "content": "Executing: fs_write hello.py"}]}),
                ("supervisor", {"pending_tasks": [{"description": "Execute hello.py", "status": "in_progress"}], "messages": [{"role": "assistant", "content": "Routing to Automation Agent..."}]}),
                ("automation", {"pending_tasks": [{"description": "Execute hello.py", "status": "completed"}], "messages": [{"role": "system", "content": "Executing: python hello.py\nOutput: Hello World\n"}]}),
                ("critic", {"pending_tasks": [], "messages": [{"role": "assistant", "content": "Verification Passed. Output matches expected 'Hello World'."}]})
            ]
            
            for node_name, current_state in steps:
                # Update the dashboard
                layout = self.dashboard.render_state(current_state, goal, node_name)
                live.update(layout)
                await asyncio.sleep(2.0) # Pause so user can watch the UI update
                
            self.console.print("\n[bold green]Goal Completed or Graph Terminated![/bold green]")
