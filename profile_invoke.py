import os
import sys
import time
import uuid
from langchain_core.messages import SystemMessage, HumanMessage
import logging

logging.basicConfig(level=logging.INFO)

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from services.agent.graph import app
from services.agent.chat_agent import SYSTEM_PROMPT

def profile_graph():
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content="Hello")
    ]
    
    for i in range(3):
        new_session = str(uuid.uuid4())
        print(f"\n--- Run {i+1} (Session: {new_session}) ---")
        t0 = time.perf_counter()
        state = app.invoke(
            {
                "messages": messages,
                "is_chat_mode": True,
                "session_id": new_session
            },
            config={"configurable": {"thread_id": new_session}}
        )
        t1 = time.perf_counter()
        print(f"Graph invoke time: {t1 - t0:.3f}s")

if __name__ == "__main__":
    profile_graph()
