import pytest
import asyncio
from agent_os.core.registry import AgentRegistry
from agent_os.workflows.engine import LangGraphEngine
from agent_os.agents.supervisor import SupervisorAgent
from agent_os.agents.base_agent import BaseAgent
from agent_os.interfaces.llm_provider import ILLMProvider

class MockLLM(ILLMProvider):
    async def generate(self, prompt: str, system_prompt: str = "", **kwargs) -> str: return '{"action": "test"}'
    async def generate_structured(self, prompt, schema, system_prompt=""): return None
    async def stream(self, prompt, system_prompt=""): return None

class MockAgent(BaseAgent):
    def __init__(self, name):
        super().__init__(name, MockLLM())
    async def process(self, state):
        return {"current_agent": self.get_name(), "next_node": "supervisor"}

def test_workflow_compilation():
    registry = AgentRegistry()
    llm = MockLLM()
    
    supervisor = SupervisorAgent(llm_provider=llm, agent_registry=registry)
    registry.register(supervisor)
    registry.register(MockAgent("browser"))
    registry.register(MockAgent("filesystem"))
    
    engine = LangGraphEngine(agent_registry=registry, supervisor=supervisor)
    graph = engine.build_graph()
    
    assert graph is not None
    
@pytest.mark.asyncio
async def test_workflow_execution():
    registry = AgentRegistry()
    llm = MockLLM()
    
    supervisor = SupervisorAgent(llm_provider=llm, agent_registry=registry)
    registry.register(supervisor)
    
    engine = LangGraphEngine(agent_registry=registry, supervisor=supervisor)
    
    initial_state = {
        "messages": [{"role": "user", "content": "test web"}],
        "current_agent": "",
        "next_node": "",
        "pending_tasks": [],
        "completed_tasks": [],
        "context": {},
        "error": None
    }
    
    # ainvoke returns the final state when END is reached.
    # The default mock Supervisor routes "web" to "browser", but "browser" is not registered, 
    # so it routes to END according to route_from_supervisor.
    result = await engine.run(initial_state, "thread_1")
    
    assert "messages" in result
    assert result["current_agent"] == "supervisor"
