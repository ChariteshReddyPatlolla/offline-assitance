import pytest
from agent_os.agents.browser import BrowserAgent
from agent_os.agents.automation import AutomationAgent
from agent_os.agents.reflection import ReflectionAgent
from agent_os.interfaces.llm_provider import ILLMProvider
from agent_os.core.models import PlannedTask
from agent_os.core.recovery import FailureAnalyzer, RecoveryEngine

class MockBrowserLLM(ILLMProvider):
    async def generate(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        return '{"tool_name": "playwright_navigate", "tool_parameters": {"url": "https://github.com"}}'
    async def generate_structured(self, p, s, sp=""): return None
    async def stream(self, p, sp=""): return None

@pytest.mark.asyncio
async def test_browser_agent_tool_conversion():
    agent = BrowserAgent(MockBrowserLLM())
    task = PlannedTask(task_id="t1", description="Go to github")
    state = {"pending_tasks": [task.model_dump()], "messages": []}
    
    result = await agent.process(state)
    assert result["next_node"] == "executor_agent"
    assert "playwright_navigate" in result["messages"][-1]["content"]

@pytest.mark.asyncio
async def test_automation_agent_tool_conversion():
    agent = AutomationAgent(MockBrowserLLM())
    task = PlannedTask(task_id="t2", description="Run git clone")
    state = {"pending_tasks": [task.model_dump()], "messages": []}
    
    result = await agent.process(state)
    assert result["next_node"] == "executor_agent"
    assert result["pending_tasks"][0]["tool_name"] == "shell_execute"
