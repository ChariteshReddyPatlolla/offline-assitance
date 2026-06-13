from typing import Any, Dict
from langgraph.graph import StateGraph, END
from ..interfaces.workflow import IWorkflowEngine
from ..core.state import AgentState
from ..agents.supervisor import SupervisorAgent
from ..agents.requirements import RequirementDiscoveryAgent
from ..agents.architect import ProjectArchitectAgent
from ..agents.antigravity_orchestrator import AntigravityOrchestratorAgent
from ..agents.development import DevelopmentLoop
from ..agents.testing import RecoveryAgent
from ..agents.completion import ProjectCompletionAgent
from ..agents.planner import PlannerAgent
from ..core.registry import AgentRegistry
from ..memory.chroma_db import ChromaMemory

class LangGraphEngine(IWorkflowEngine):
    """
    Production-ready LangGraph orchestration engine.
    Wires up the Supervisor and other specialized agents using the AgentRegistry.
    """
    def __init__(self, agent_registry: AgentRegistry, supervisor: SupervisorAgent):
        self.agent_registry = agent_registry
        self.supervisor = supervisor
        self.graph = None

    def build_graph(self) -> Any:
        """
        Constructs the LangGraph state machine.
        """
        workflow = StateGraph(AgentState)

        # 1. Add Supervisor Node
        workflow.add_node("supervisor", self.supervisor.process)
        workflow.add_node("discovery", RequirementDiscoveryAgent(self.supervisor._llm_provider).process)
        workflow.add_node("architect", ProjectArchitectAgent(self.supervisor._llm_provider).process)
        workflow.add_node("planner", PlannerAgent(self.supervisor._llm_provider).process)
        workflow.add_node("antigravity_orchestrator", AntigravityOrchestratorAgent(self.supervisor._llm_provider).process)
        workflow.add_node("development_loop", DevelopmentLoop(self.supervisor._llm_provider).process)
        workflow.add_node("recovery_agent", RecoveryAgent(self.supervisor._llm_provider, ChromaMemory()).process)
        workflow.add_node("completion_agent", ProjectCompletionAgent(self.supervisor._llm_provider, ChromaMemory()).process)

        # 2. Add Specialized Agent Nodes
        agents = self.agent_registry.list_agents()
        for name, agent in agents.items():
            if name != "supervisor":
                workflow.add_node(name, agent.process)

        # 3. Define Entry Point
        workflow.set_entry_point("supervisor")

        # 4. Define Conditional Edges from Supervisor
        # The supervisor determines the 'next_node' in its state output
        def route_from_supervisor(state: AgentState):
            next_agent = state.get("next_node", "END")
            core_nodes = ["discovery", "architect", "planner", "antigravity_orchestrator", "development_loop", "recovery_agent", "completion_agent"]
            if next_agent == "END" or (next_agent not in agents and next_agent not in core_nodes):
                return END
            return next_agent

        # Map all possible agents to themselves in the conditional edge
        route_mapping = {name: name for name in agents.keys() if name != "supervisor"}
        
        # Explicitly add core nodes to the route mapping
        core_nodes = ["discovery", "architect", "planner", "antigravity_orchestrator", "development_loop", "recovery_agent", "completion_agent"]
        for node in core_nodes:
            route_mapping[node] = node
            
        route_mapping[END] = END
        
        workflow.add_conditional_edges("supervisor", route_from_supervisor, route_mapping)
        
        # 5. Define edges back to Supervisor from all specialized agents
        for name in agents.keys():
            if name != "supervisor":
                workflow.add_edge(name, "supervisor")
                
        # Also define edges back for core nodes
        for node in core_nodes:
            workflow.add_edge(node, "supervisor")

        # Compile graph
        self.graph = workflow.compile()
        return self.graph

    async def run(self, initial_state: Dict[str, Any], thread_id: str) -> Dict[str, Any]:
        """
        Execute the compiled graph with the initial state asynchronously.
        """
        if not self.graph:
            self.build_graph()
            
        config = {"configurable": {"thread_id": thread_id}}
        return await self.graph.ainvoke(initial_state, config=config)
