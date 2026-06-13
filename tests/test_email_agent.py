import pytest
import asyncio
from typing import Any, Dict
from agent_os.agents.email_agent import EmailAgent
from agent_os.interfaces.llm_provider import ILLMProvider
from agent_os.core.models import PlannedTask

class MockEmailLLM(ILLMProvider):
    async def generate(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        if "read" in prompt.lower():
            return '{"tool_name": "read_emails", "tool_parameters": {"folder": "INBOX", "limit": 5}}'
        return '{"tool_name": "send_email", "tool_parameters": {"to": "test@example.com", "subject": "Test", "body": "Body"}}'
        
    async def generate_structured(self, p, s, sp=""): return None
    async def stream(self, p, sp=""): return None

@pytest.mark.asyncio
async def test_email_agent_tool_conversion():
    agent = EmailAgent(MockEmailLLM())
    
    # Test reading emails
    state1 = {"pending_tasks": [], "messages": [{"role": "user", "content": "Read my latest emails"}]}
    result1 = await agent.process(state1)
    
    assert result1["next_node"] == "executor_agent"
    assert "read_emails" in result1["messages"][-1]["content"]
    
    # Test sending emails
    state2 = {"pending_tasks": [], "messages": [{"role": "user", "content": "Send an email to John"}]}
    result2 = await agent.process(state2)
    
    assert result2["next_node"] == "executor_agent"
    assert "send_email" in result2["messages"][-1]["content"]
