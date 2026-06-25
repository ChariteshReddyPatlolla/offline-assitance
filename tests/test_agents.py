import pytest
import asyncio
from typing import Any, Dict
from agent_os.agents.supervisor import SupervisorAgent
from agent_os.agents.coding import CodingAgent
from agent_os.agents.critic import CriticAgent
from agent_os.agents.automation import AutomationAgent
from agent_os.interfaces.llm_provider import ILLMProvider

class MockLLM(ILLMProvider):
    def __init__(self, return_value="coding"):
        self.return_value = return_value

    async def generate(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        return self.return_value
        
    async def generate_structured(self, prompt, schema, system_prompt=""): return None
    async def stream(self, prompt, system_prompt=""): return None

# We can mock AgentRegistry since we only need it if Supervisor relies on it
class MockRegistry:
    pass

@pytest.mark.asyncio
async def test_supervisor_dynamic_routing_success():
    llm = MockLLM(return_value="coding")
    supervisor = SupervisorAgent(llm_provider=llm, agent_registry=MockRegistry())
    
    state = {
        "messages": [{"content": "Write a python script to sort an array."}],
        "pending_tasks": []
    }
    
    result = await supervisor.process(state)
    assert result["next_node"] == "coding"

@pytest.mark.asyncio
async def test_supervisor_dynamic_routing_fallback():
    # If LLM returns garbage, it should fallback to END or default
    llm = MockLLM(return_value="UNKNOWN_AGENT_NAME")
    supervisor = SupervisorAgent(llm_provider=llm, agent_registry=MockRegistry())
    
    state = {
        "messages": [{"content": "Plan the task"}],
        "pending_tasks": []
    }
    
    # "plan" in content -> fallback logic routes to "planner"
    result = await supervisor.process(state)
    assert result["next_node"] == "planner"

@pytest.mark.asyncio
async def test_coding_agent():
    # Test tool generation routing
    agent1 = CodingAgent(llm_provider=MockLLM(return_value="write_file(...)"))
    result1 = await agent1.process({"messages": []})
    assert result1["next_node"] == "executor_agent"
    assert "write_file" in result1["messages"][-1]["content"]

    # Test END routing
    agent2 = CodingAgent(llm_provider=MockLLM(return_value="END"))
    result2 = await agent2.process({"messages": []})
    assert result2["next_node"] == "critic"
    assert "Code generated." in result2["messages"][-1]["content"]

@pytest.mark.asyncio
async def test_critic_agent():
    agent = CriticAgent(llm_provider=MockLLM())
    result = await agent.process({"messages": []})
    assert result["next_node"] == "supervisor"
    assert "Review passed." in result["messages"][-1]["content"]

@pytest.mark.asyncio
async def test_automation_agent():
    agent = AutomationAgent(llm_provider=MockLLM())
    result = await agent.process({"messages": []})
    assert result["next_node"] == "supervisor"
