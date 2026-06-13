import os
import sys
import json
import time
import logging
import re
import uuid
import redis
from contextlib import contextmanager

# Add parent dir to path to resolve imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from langchain_core.messages import AIMessage, messages_from_dict
from shared.database import SessionLocal
from shared import models
from services.agent.graph import app

APPROVAL_PATTERN = re.compile(r"\[NEEDS_APPROVAL:([^\]]+)\]")
CHECKLIST_PATTERN = re.compile(r"\[CHECKLIST_REQUEST:([^\|]+)\|(.*?)\]", re.DOTALL)

def _extract_approval_request(content: str) -> dict | None:
    match = APPROVAL_PATTERN.search(content)
    if match:
        return {"action_key": match.group(1)}
    return None

def _extract_checklist_request(content: str) -> dict | None:
    match = CHECKLIST_PATTERN.search(content)
    if match:
        try:
            return {
                "action_key": match.group(1).strip(),
                "data": json.loads(match.group(2).strip())
            }
        except Exception as e:
            logger.error("Failed to parse checklist JSON: %s", e)
    return None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

r = redis.Redis(host='localhost', port=6379, db=0)

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def process_task(task_payload):
    session_id = task_payload["session_id"]
    file_path = task_payload["file_path"]
    langchain_messages = messages_from_dict(task_payload["messages"])

    logger.info("Starting background LLM execution for session: %s", session_id)
    
    try:
        # Await is not natively supported in a sync while loop unless we use asyncio.run
        import asyncio
        final_state = asyncio.run(app.ainvoke(
            {"messages": langchain_messages},
            config={"configurable": {"thread_id": session_id, "checkpoint_ns": "chat"}}
        ))
    except Exception as e:
        logger.exception("Graph execution failed")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# Error\nThe background agent encountered an error:\n```\n{str(e)}\n```")
        return

    # Extract final response
    agent_response = "I'm sorry, I was unable to generate a response."
    for msg in reversed(final_state["messages"]):
        if msg.content and isinstance(msg.content, str) and msg.content.strip():
            temp_approval = _extract_approval_request(msg.content.strip())
            temp_checklist = _extract_checklist_request(msg.content.strip())
            
            if temp_checklist:
                agent_response = msg.content.strip()
                agent_response = CHECKLIST_PATTERN.sub("", agent_response).strip()
                break
            elif temp_approval:
                agent_response = msg.content.strip()
                break
            elif isinstance(msg, AIMessage):
                agent_response = msg.content.strip()
                break

    # Save to database and update session context
    with get_db() as db:
        session = db.query(models.Session).filter(models.Session.id == session_id).first()
        if session:
            # Parse context_state block
            context_match = re.search(r"```(?:context_state|json)?\s*({.*?})\s*```", agent_response, re.DOTALL)
            if context_match:
                try:
                    state_data = json.loads(context_match.group(1))
                    if "current_app" in state_data: session.current_app = state_data["current_app"]
                    if "current_directory" in state_data: session.current_directory = state_data["current_directory"]
                    if "current_file" in state_data: session.current_file = state_data["current_file"]
                    if "open_tabs" in state_data: session.open_tabs = json.dumps(state_data["open_tabs"])
                    if "last_action" in state_data: session.last_action = state_data["last_action"]
                    db.commit()
                except Exception:
                    pass
                agent_response = re.sub(r"```(?:context_state|json)?\s*({.*?})\s*```", "", agent_response, flags=re.DOTALL).strip()

            # Save AIMessages and ToolMessages
            new_messages = final_state["messages"][len(langchain_messages):]
            for msg in new_messages:
                if isinstance(msg, AIMessage):
                    tc_json = json.dumps(msg.tool_calls) if hasattr(msg, "tool_calls") and msg.tool_calls else ""
                    db_msg = models.Message(session_id=session_id, role="assistant", content=msg.content or "", tool_calls=tc_json)
                    db.add(db_msg)
                elif msg.__class__.__name__ == "ToolMessage":
                    db_msg = models.Message(session_id=session_id, role="tool", content=str(msg.content), name=getattr(msg, "name", ""), tool_call_id=getattr(msg, "tool_call_id", ""))
                    db.add(db_msg)
            db.commit()

    # Write output to the VS Code file so user can see it
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# Agent Output\n\n{agent_response}")
        logger.info("Successfully wrote output to %s", file_path)
    except Exception as e:
        logger.error("Failed to write to VS Code file: %s", e)


def main():
    logger.info("Background Worker started. Listening on Redis queue 'llm_task_queue'...")
    while True:
        try:
            # blpop blocks until an item is available
            item = r.blpop("llm_task_queue", timeout=0)
            if item:
                _, payload_bytes = item
                task_payload = json.loads(payload_bytes.decode('utf-8'))
                process_task(task_payload)
        except Exception as e:
            logger.error("Worker error: %s", e)
            time.sleep(1)

if __name__ == "__main__":
    main()
