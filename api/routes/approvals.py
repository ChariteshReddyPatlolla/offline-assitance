"""
Approval API routes — list pending approvals and accept/deny them in-chat.
"""
import os
import logging
import re
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from shared import schemas, models
from shared.database import get_db
from services.tools.approval_store import grant_approval, deny_approval, get_all_pending, get_pending_for_session
from langchain_core.messages import HumanMessage, AIMessage

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/pending")
def get_pending_approvals():
    """Get all currently pending approval requests."""
    return {"pending": get_all_pending()}


@router.get("/pending/{session_id}")
def get_pending_for_session_route(session_id: str):
    """Get pending approvals for a specific session."""
    return {"pending": get_pending_for_session(session_id)}


@router.post("/decide")
async def decide_approval(request: schemas.ApproveRequest, db: Session = Depends(get_db)):
    """
    Approve or deny an action, then re-run the agent with the original message.
    If approved: grants the action, re-invokes agent so it executes.
    If denied: cancels the action, notifies agent.
    """
    from services.agent.graph import app as agent_app

    action_key = request.action_key
    tool_executed = False
    tool_output = ""

    # Fetch session early
    session = db.query(models.Session).filter(models.Session.id == request.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if request.approved:
        grant_approval(action_key)
        logger.info("User APPROVED action: %s", action_key)
        
        # Try to find and execute the matching tool call directly
        # to ensure it actually runs and local LLMs don't bypass it.
        try:
            # Reconstruct past messages list to look for the matching tool call
            past_messages = (
                db.query(models.Message)
                .filter(models.Message.session_id == request.session_id)
                .order_by(models.Message.created_at)
                .all()
            )
            
            from services.agent.graph import parse_fallback_tool_calls
            from langchain_core.messages import AIMessage
            
            tool_call_to_run = None
            for msg in reversed(past_messages):
                if msg.role == "assistant":
                    tool_calls = []
                    # First try to load native tool calls saved in DB
                    if msg.tool_calls:
                        try:
                            tool_calls = json.loads(msg.tool_calls)
                        except Exception:
                            pass
                    
                    # Fallback to parsing from content if empty
                    if not tool_calls:
                        temp_ai_msg = parse_fallback_tool_calls(AIMessage(content=msg.content))
                        tool_calls = getattr(temp_ai_msg, "tool_calls", []) or []

                    if tool_calls:
                        for tc in tool_calls:
                            tc_name = tc.get("name")
                            tc_args = tc.get("args", {})
                            
                            is_match = False
                            if action_key.startswith("shell:") and tc_name == "execute_shell_command":
                                cmd = tc_args.get("command", "")
                                if action_key == f"shell:{cmd[:200]}":
                                    is_match = True
                            elif action_key.startswith("write:") and tc_name == "write_file":
                                filepath = tc_args.get("filepath", "")
                                if filepath and action_key == f"write:{os.path.abspath(filepath)}":
                                    is_match = True
                            elif action_key.startswith("delete:") and tc_name == "delete_file":
                                filepath = tc_args.get("filepath", "")
                                if filepath and action_key == f"delete:{os.path.abspath(filepath)}":
                                    is_match = True
                            elif action_key.startswith(f"{tc_name}:"):
                                is_match = True
                                
                            if is_match:
                                tool_call_to_run = (tc_name, tc_args)
                                break
                if tool_call_to_run:
                    break
            
            if tool_call_to_run:
                tc_name, tc_args = tool_call_to_run
                logger.info("Found matching tool call to run directly: name=%s, args=%s", tc_name, tc_args)
                
                # Find the tool in all_tools
                from services.agent.graph import all_combined_tools as all_tools
                tool_func = None
                for t in all_tools:
                    if getattr(t, "name", t.__class__.__name__) == tc_name:
                        tool_func = t
                        break
                
                if tool_func:
                    # Run in active session directory context
                    from shared.context import active_session_dir
                    token = active_session_dir.set(session.current_directory)
                    try:
                        tool_output = tool_func.invoke(tc_args)
                        tool_executed = True
                        logger.info("Direct tool execution succeeded: %s", tool_output)
                        
                        # Manually update session context since tool ran directly
                        if tc_name == "execute_shell_command":
                            cmd = tc_args.get("command", "").strip()
                            session.last_action = f"Ran shell command: {cmd}"
                            cd_match = re.match(r"^cd\s+(.+)$", cmd, re.IGNORECASE)
                            if cd_match:
                                session.current_directory = os.path.abspath(cd_match.group(1))
                        elif tc_name == "write_file":
                            filepath = tc_args.get("filepath", "")
                            if filepath:
                                session.current_file = os.path.abspath(filepath)
                                session.current_directory = os.path.dirname(session.current_file)
                                session.last_action = f"Wrote to file {os.path.basename(session.current_file)}"
                        elif tc_name == "delete_file":
                            filepath = tc_args.get("filepath", "")
                            if filepath:
                                session.last_action = f"Deleted file {os.path.basename(filepath)}"
                        elif tc_name == "create_directory":
                            path = tc_args.get("path", "")
                            if path:
                                session.current_directory = os.path.abspath(path)
                                session.last_action = f"Created directory {os.path.basename(session.current_directory)}"
                        elif tc_name == "open_application":
                            app_name = tc_args.get("app_name", "")
                            if app_name:
                                session.current_app = app_name
                                session.last_action = f"Opened application {app_name}"
                                app_path = tc_args.get("path")
                                if app_path:
                                    abs_app_path = os.path.abspath(app_path)
                                    if os.path.isdir(abs_app_path) or (not os.path.exists(abs_app_path) and not os.path.basename(abs_app_path).count('.')):
                                        session.current_directory = abs_app_path
                                    else:
                                        session.current_file = abs_app_path
                                        session.current_directory = os.path.dirname(abs_app_path)
                        elif tc_name == "close_application":
                            app_name = tc_args.get("app_name", "")
                            if app_name:
                                if session.current_app and session.current_app.lower() == app_name.lower():
                                    session.current_app = None
                                session.last_action = f"Closed application {app_name}"
                        db.commit()
                    finally:
                        active_session_dir.reset(token)
                else:
                    logger.warning("Tool function %s not found in all_tools", tc_name)
        except Exception as e_direct:
            logger.exception("Failed during direct tool execution flow: %s", str(e_direct))

        if tool_executed:
            decision_note = (
                f"[SYSTEM: TOOL ALREADY EXECUTED]\n"
                f"The user approved the action '{action_key}', and the system HAS ALREADY EXECUTED IT successfully.\n"
                f"Result:\n{tool_output}\n\n"
                f"CRITICAL INSTRUCTION: DO NOT CALL ANY TOOLS. The tool was already run. Just write a short conversational message telling the user it was successful."
            )
        else:
            decision_note = f"[USER_APPROVED:{action_key}] The user approved this action. Please proceed and execute it now."
    else:
        deny_approval(action_key)
        logger.info("User DENIED action: %s", action_key)
        decision_note = f"[USER_DENIED:{action_key}] The user denied this action. Acknowledge and do NOT execute it."

    # Fetch session message history

    past_messages = (
        db.query(models.Message)
        .filter(models.Message.session_id == request.session_id)
        .order_by(models.Message.created_at)
        .all()
    )

    langchain_messages = []
    for msg in past_messages:
        if msg.role == "user":
            langchain_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            langchain_messages.append(AIMessage(content=msg.content))

    # Append the approval decision as a system note
    langchain_messages.append(HumanMessage(content=decision_note))

    try:
        final_state = agent_app.invoke({"messages": langchain_messages})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error after approval: {str(e)}")

    # Extract agent response
    agent_response = "Action processed." if request.approved else "Action cancelled as requested."
    for msg in reversed(final_state["messages"]):
        if isinstance(msg, AIMessage) and msg.content and isinstance(msg.content, str) and msg.content.strip():
            agent_response = msg.content.strip()
            break

    # Look for a context_state block in the agent response
    context_match = re.search(r"```(?:context_state|json)?\s*({.*?})\s*```", agent_response, re.DOTALL)
    if context_match:
        try:
            state_data = json.loads(context_match.group(1))
            if "current_app" in state_data:
                session.current_app = state_data["current_app"]
            if "current_directory" in state_data:
                session.current_directory = state_data["current_directory"]
            if "current_file" in state_data:
                session.current_file = state_data["current_file"]
            if "open_tabs" in state_data:
                session.open_tabs = json.dumps(state_data["open_tabs"])
            if "last_action" in state_data:
                session.last_action = state_data["last_action"]
            db.commit()
            logger.info("Successfully updated session context state from agent: %s", state_data)
        except Exception as e:
            logger.warning("Failed to parse context_state JSON: %s", str(e))
        
        # Clean the agent response to strip the context_state block so the user never sees it in the chat UI
        agent_response = re.sub(r"```(?:context_state|json)?\s*({.*?})\s*```", "", agent_response, flags=re.DOTALL).strip()

    # Save response to DB
    assistant_msg = models.Message(
        session_id=request.session_id,
        role="assistant",
        content=agent_response
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return schemas.Message.model_validate(assistant_msg)
