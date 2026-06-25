from typing import Any, Dict
from .base_agent import BaseAgent
from ..interfaces.llm_provider import ILLMProvider
from ..core.registry import AgentRegistry
import json

class SupervisorAgent(BaseAgent):
    """
    The Supervisor Agent coordinates execution by receiving goals, routing work, 
    and tracking execution across specialized agents.
    """
    def __init__(self, llm_provider: ILLMProvider, agent_registry: AgentRegistry):
        super().__init__(name="supervisor", llm_provider=llm_provider)
        self._agent_registry = agent_registry
        self._capabilities = ["goal_decomposition", "task_routing", "execution_monitoring"]
        
        # Load memory instance here for resume logic
        from ..memory.chroma_db import ChromaMemory
        self.chroma = ChromaMemory()

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # Look at the most recent message or the top pending task
        latest_message = state["messages"][-1].get("content", "") if state.get("messages") else ""
        pending_tasks = state.get("pending_tasks", [])
        
        target = latest_message
        if pending_tasks:
            target = pending_tasks[0].get("description", "")

        if not target:
            return {"next_node": "END", "current_agent": self.get_name()}

        # Construct a prompt for dynamic routing
        agents_list = [
            "discovery", "architect", "planner", "antigravity_orchestrator", "development_loop", "recovery_agent", "completion_agent", "coding", "automation", "browser", "research", 
            "knowledge", "memory_agent", "critic", "notification", "executor_agent", "reflection", "vscode", "email_agent", "END"
        ]
        
        system_prompt = f"""
        You are a highly capable Supervisor Router.
        Analyze the goal: "{target}"
        Return EXACTLY ONE of the following agent names that should handle this:
        {agents_list}
        Do not output any other text.
        """
        
        try:
            # Dynamically request the route from the LLM
            response = await self.llm.generate(prompt=target, system_prompt=system_prompt)
            next_agent = response.strip().lower()
            if next_agent not in agents_list:
                raise ValueError("Invalid agent returned")
        except Exception:
            # Fallback mock routing if LLM is unavailable
            content = target.lower()
            next_agent = "END"
            if any(phrase in content for phrase in ["idea", "want a", "build a", "create a"]):
                next_agent = "discovery"
            elif any(phrase in content for phrase in ["architect", "schema", "database", "api", "tech stack"]):
                next_agent = "architect"
            elif "code" in content or "script" in content or "debug" in content:
                next_agent = "coding"
            elif "web" in content or "browse" in content or "youtube" in content or "search web" in content or "play video" in content:
                next_agent = "browser"
            elif "search" in content or "research" in content:
                next_agent = "research"
            elif "review" in content or "mistake" in content:
                next_agent = "critic"
            elif "automate" in content or "desktop" in content or "shell" in content:
                next_agent = "automation"
            elif "email" in content or "mail" in content or "inbox" in content or "draft" in content or "send to" in content:
                next_agent = "email_agent"
            elif "vscode" in content or "editor" in content or "endpoint" in content or "open file" in content:
                next_agent = "vscode"
            elif "context" in content or "memory" in content:
                next_agent = "knowledge"
            elif "plan" in content:
                next_agent = "planner"
            elif any(phrase in content for phrase in ["antigravity", "orchestrator", "manager", "worker"]):
                next_agent = "antigravity_orchestrator"
            elif any(phrase in content for phrase in ["development loop", "execute dag", "start coding loop", "autonomous loop"]):
                next_agent = "development_loop"
            elif any(phrase in content for phrase in ["test and recover", "run test", "fix error", "recovery"]):
                next_agent = "recovery_agent"
            elif any(phrase in content for phrase in ["finish project", "complete project", "wrap up"]):
                next_agent = "completion_agent"
            elif "continue" in content and "project" in content:
                # E.g. "Continue the stock prediction project"
                import json
                
                project_name = content.split("continue the")[1].split("project")[0].strip()
                results = self.chroma.query_memory(
                    collection_name="saved_projects",
                    query_texts=[project_name],
                    n_results=1
                )
                
                if results and results.get("documents") and results["documents"][0]:
                    try:
                        meta = results["metadatas"][0][0]
                        state_data = json.loads(meta.get("state_json", "{}"))
                        
                        # Rehydrate state
                        state["architecture"] = state_data.get("architecture", {})
                        state["execution_plan"] = state_data.get("execution_plan", {})
                        state["messages"].append({"role": "assistant", "content": f"Resumed project: {project_name}. Routing to planner."})
                        next_agent = "planner"
                    except Exception as e:
                        state["messages"].append({"role": "assistant", "content": f"Could not resume project: {str(e)}"})
                        next_agent = "END"
                else:
                    state["messages"].append({"role": "assistant", "content": f"Project '{project_name}' not found in persistent memory."})
                    next_agent = "END"

        return {
            "next_node": next_agent,
            "current_agent": self.get_name(),
            "messages": state.get("messages", [])
        }
