from rich.layout import Layout
from rich.panel import Panel
from rich.console import Console
from rich.table import Table
from rich.text import Text
from typing import Dict, Any, List

class OSDashboard:
    """
    Renders the live state of the Local Autonomous Agent OS.
    Displays active tasks, execution logs, and current agent.
    """
    def __init__(self, console: Console):
        self.console = console
        self.layout = Layout()
        
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        self.layout["main"].split_row(
            Layout(name="tasks", ratio=1),
            Layout(name="logs", ratio=2)
        )
        
    def render_state(self, state: Dict[str, Any], goal: str, active_agent: str):
        """Updates the layout panels based on the LangGraph state."""
        
        # 1. Header
        header = Panel(Text(f"Agent OS | Autonomous Project Mode | Goal: {goal}", style="bold white on blue"))
        self.layout["header"].update(header)
        
        # 2. Tasks Panel
        tasks_table = Table(show_header=True, header_style="bold magenta", expand=True)
        tasks_table.add_column("Status", width=10)
        tasks_table.add_column("Agent", width=12)
        tasks_table.add_column("Description")
        
        pending = state.get("pending_tasks", [])
        for t in pending:
            status = t.get("status", "pending")
            color = "yellow" if status == "in_progress" else "green" if status == "completed" else "red" if status == "failed" else "white"
            tasks_table.add_row(
                f"[{color}]{status}[/{color}]", 
                "TBD", # The explicit agent target might not be in the abstract dictionary
                t.get("description", "")[:50] + "..."
            )
            
        self.layout["tasks"].update(Panel(tasks_table, title="[bold]Execution DAG[/bold]"))
        
        # 3. Logs Panel
        messages = state.get("messages", [])
        log_text = ""
        for msg in messages[-15:]: # Show last 15 messages
            role = msg.get("role", "system")
            content = str(msg.get("content", ""))
            color = "cyan" if role == "assistant" else "magenta"
            log_text += f"[{color}]{role.upper()}[/{color}]: {content}\n"
            
        self.layout["logs"].update(Panel(log_text, title=f"[bold]Execution Logs (Active Node: {active_agent})[/bold]"))
        
        # 4. Footer
        footer = Panel(Text(f"Risk Gates Active | Reflection Enabled", style="bold green"))
        self.layout["footer"].update(footer)
        
        return self.layout
