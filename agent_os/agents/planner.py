import json
from typing import Any, Dict
from .base_agent import BaseAgent
from ..interfaces.llm_provider import ILLMProvider
from ..core.models import ExecutionPlan

class PlannerAgent(BaseAgent):
    """
    The Project Planning Agent decomposes architectural requirements into an executable DAG of tasks.
    """
    def __init__(self, llm_provider: ILLMProvider):
        super().__init__(name="planner", llm_provider=llm_provider)
        self._capabilities = ["task_decomposition", "dependency_resolution", "dynamic_replanning"]

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        architecture = state.get("architecture", {})
        messages = state.get("messages", [])
        
        # Build prompt using architecture if available
        prompt = "Act as an experienced Software Engineering Manager & Project Planner.\n\n"
        if architecture:
            prompt += f"Based on the following approved Project Architecture:\n{json.dumps(architecture, indent=2)}\n\n"
        else:
            goal = messages[-1].get("content", "") if messages else "Unknown Goal"
            prompt += f"Decompose this goal into a structured ExecutionPlan:\n{goal}\n\n"
            
        prompt += """
        Generate an ExecutionPlan that contains:
        1. Task list (with specific tool capabilities like 'filesystem', 'browser', 'coding')
        2. Dependency graph (DAG)
        3. Milestones
        4. Parallelizable tasks
        
        Ensure you do not generate any raw code implementation, only the execution plan structure.
        Output ONLY valid JSON matching the ExecutionPlan schema exactly.
        """
        
        schema = ExecutionPlan.model_json_schema()
        
        try:
            res = await self._llm_provider.generate_structured(prompt=prompt, schema=schema, system_prompt="You are a Project Manager. Output valid JSON matching the schema.")
            if res:
                plan_data = res
            else:
                raise ValueError("Structured generation returned empty")
        except Exception:
            # Fallback
            res = await self._llm_provider.generate(prompt=f"{prompt}\n\nOutput ONLY valid JSON matching this schema:\n{json.dumps(schema, indent=2)}", system_prompt="Output ONLY valid JSON.")
            try:
                if "```json" in res:
                    res = res.split("```json")[1].split("```")[0].strip()
                elif "```" in res:
                    res = res.split("```")[1].split("```")[0].strip()
                plan_data = json.loads(res)
            except Exception:
                plan_data = {
                    "original_goal": "Failed to parse JSON plan.",
                    "tasks": [],
                    "dag": {},
                    "milestones": [],
                    "parallelizable_tasks": []
                }

        # Save to memory index if available
        try:
            from services.session_manager import session_manager
            if hasattr(session_manager, 'indexer') and session_manager.indexer and hasattr(session_manager.indexer, 'vector_store'):
                session_manager.indexer.vector_store.add_memory(
                    collection_name="semantic_memory",
                    documents=[json.dumps(plan_data, indent=2)],
                    metadatas=[{"type": "execution_plan", "source": "planner"}],
                    ids=["execution_plan_latest"]
                )
        except Exception:
            pass

        # Build visual representation
        content = "Here is the Executable Project Plan:\n\n"
        
        if "milestones" in plan_data and plan_data["milestones"]:
            content += "**Milestones:**\n"
            for m in plan_data["milestones"]:
                content += f"- {m}\n"
            content += "\n"
            
        if "parallelizable_tasks" in plan_data and plan_data["parallelizable_tasks"]:
            content += "**Parallelizable Task Groups:**\n"
            for i, group in enumerate(plan_data["parallelizable_tasks"]):
                content += f"- Group {i+1}: {', '.join(group)}\n"
            content += "\n"
            
        content += "**Task Graph:**\n```text\n"
        
        # Basic visual hierarchy rendering
        tasks = plan_data.get("tasks", [])
        dag = plan_data.get("dag", {})
        
        # Group tasks by some logical prefix if possible (e.g. Backend_, Frontend_)
        # We will attempt a rudimentary tree visualization using dependencies
        root_tasks = [t for t in tasks if not t.get("dependencies")]
        
        def render_tree(task_id, level):
            task = next((t for t in tasks if t.get("task_id") == task_id), None)
            if task:
                desc = task.get("description", task_id)
                prefix = " " * (level * 2) + " \u251c\u2500 " if level > 0 else ""
                lines.append(f"{prefix}{task_id}: {desc}")
                children = dag.get(task_id, [])
                for child in children:
                    render_tree(child, level + 1)
                    
        lines = []
        if root_tasks:
            for rt in root_tasks:
                render_tree(rt.get("task_id", ""), 0)
        else:
            # Fallback flat list
            for t in tasks:
                lines.append(f" \u251c\u2500 {t.get('task_id', 'unknown')}: {t.get('description', '')}")
                
        content += "\n".join(lines)
        content += "\n```\n\n*(Ready to begin execution when approved. No code has been generated yet.)*"

        return {
            "current_agent": self.get_name(),
            "next_node": "END", # Stop so user can review the plan
            "execution_plan": plan_data,
            "messages": messages + [{"role": "assistant", "content": content}]
        }
