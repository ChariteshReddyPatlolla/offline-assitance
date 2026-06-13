import asyncio
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
import sys

# Ensure local imports work
sys.path.append(os.getcwd())

from agent_os.agents.supervisor import SupervisorAgent
from agent_os.core.runner import OSRunner
from agent_os.interfaces.llm_provider import ILLMProvider
from typing import Any

class MockLLM(ILLMProvider):
    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        return "{}"
    async def generate_structured(self, prompt: str, schema: Any, system_prompt: str = "") -> Any:
        return None
    async def stream(self, prompt: str, system_prompt: str = ""):
        yield ""

async def main():
    # 1. Initialize the Supervisor (which compiles the LangGraph)
    print("Initializing Agent OS LangGraph...")
    mock_llm = MockLLM()
    agent_registry = {
        "planner": None,
        "browser": None,
        "automation": None,
        "coding": None,
        "critic": None
    }
    supervisor = SupervisorAgent(llm_provider=mock_llm, agent_registry=agent_registry)
    
    # 2. Initialize the Runner with the Dashboard
    runner = OSRunner(supervisor)
    
    # 3. Kick off the autonomous loop for the Hello World task
    goal = "Open VSCode, create hello.py, write a Python program that prints Hello World, save the file, and execute the file."
    await runner.run_autonomous(goal)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nAgent OS Terminated by user.")
