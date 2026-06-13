import asyncio
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
import json
import logging
from typing import Any

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from agent_os.core.registry import AgentRegistry, ToolRegistry
from agent_os.workflows.engine import LangGraphEngine
from agent_os.agents.supervisor import SupervisorAgent
from agent_os.interfaces.llm_provider import ILLMProvider
from agent_os.core.permissions import PermissionManager
from agent_os.memory.chroma_db import ChromaMemory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RealOS_Test")

class OllamaProvider(ILLMProvider):
    def __init__(self):
        self.llm = ChatOllama(model="llama3.1:8b", temperature=0.1)
        
    async def generate(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))
        res = self.llm.invoke(messages)
        return res.content

    async def generate_structured(self, prompt: str, schema: dict, system_prompt: str = "") -> dict:
        messages = []
        sys_p = system_prompt + f"\n\nYou MUST return ONLY valid JSON that matches this schema:\n{json.dumps(schema)}"
        messages.append(SystemMessage(content=sys_p))
        messages.append(HumanMessage(content=prompt))
        res = self.llm.invoke(messages)
        content = res.content
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            return json.loads(content.strip())
        except Exception:
            return None

    async def stream(self, prompt: str, system_prompt: str = ""):
        yield ""

async def run_project():
    logger.info("Initializing AgentOS with Ollama")
    
    agent_registry = AgentRegistry()
    llm = OllamaProvider()
    
    supervisor = SupervisorAgent(llm_provider=llm, agent_registry=agent_registry)
    registry = AgentRegistry()
    registry.register(supervisor)
    
    engine = LangGraphEngine(agent_registry=registry, supervisor=supervisor)
    
    state = {
        "messages": [{"role": "user", "content": "I want a simple hello world app in Python"}],
        "current_agent": "",
        "next_node": "",
        "pending_tasks": [],
        "completed_tasks": [],
        "context": {},
        "error": None
    }
    
    logger.info(f"User Request: {state['messages'][0]['content']}")
    
    for i in range(10):
        logger.info(f"\n--- Turn {i+1} ---")
        state = await engine.run(state, "real_thread")
        last_msg = state["messages"][-1] if state.get("messages") else {}
        logger.info(f"[{state.get('current_agent')}] {last_msg.get('content', '')}")
        
        if state.get("next_node") == "END":
            # Auto-reply to push it forward
            reply = "Looks good, continue."
            logger.info(f"[user] {reply}")
            state["messages"].append({"role": "user", "content": reply})
            state["next_node"] = ""
            
        if "Project Complete!" in last_msg.get("content", ""):
            logger.info("Finished successfully!")
            break

if __name__ == "__main__":
    asyncio.run(run_project())
