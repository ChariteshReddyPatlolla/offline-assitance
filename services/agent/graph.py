import re
import json
import uuid
import logging
from langgraph.graph import StateGraph, START, END
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage,AIMessage,HumanMessage
from langgraph.prebuilt import ToolNode
from services.agent.state import AgentState
from services.tools import (
    all_tools,
    open_application,
    close_application,
    search_start_menu,
    focus_application,
    minimize_application,
    maximize_application,
    press_hotkey,
    type_text_at_cursor,
    read_file,
    write_file,
    delete_file,
    list_directory,
    create_directory,
    execute_shell_command,
    git_status,
    git_log,
    git_diff,
    analyze_repo,
    git_add,
    git_commit,
    git_checkout,
    git_branch,
    open_url_in_browser,
    search_youtube,
    pause_playback,
    resume_playback,
    web_search,
    research_topic,
    send_email,
    send_email_fast,
    save_to_drafts,
    read_emails,
    search_emails,
    extract_pdf_text,
    summarize_pdf,
    run_editor_sync_demo,
    read_query,
    write_query,
    list_tables,
    describe_table,
    browser_navigate,
    browser_click,
    browser_type,
    browser_wait_for,
    browser_take_screenshot,
    browser_close,
    browser_scroll,
    browser_extract_text,
    list_browser_tabs,
    switch_browser_tab,
    search_files,
    move_file,
    extract_pdf_tables,
    split_pdf,
    merge_pdfs,
    scrape_page,
    extract_links,
    open_file_in_vscode,
    open_folder_in_vscode,
    run_command_in_vscode_terminal,
    execute_workflow,
    search_jobs,
)
from workflows.automation_workflows import (
    create_python_project,
    modify_file_and_rerun,
    browser_research_and_save,
    youtube_search_and_play,
    git_commit_and_push,
    research_and_email,
    analyze_resume_skills,
)

logger = logging.getLogger(__name__)

# Combined list of tools starting with custom tools and high-level workflow tools
workflow_tools = [
    create_python_project,
    modify_file_and_rerun,
    browser_research_and_save,
    youtube_search_and_play,
    git_commit_and_push,
    research_and_email,
    analyze_resume_skills,
]

all_combined_tools = list(all_tools) + workflow_tools
mcp_tools = []
unique_mcp_tools = []

SYSTEM_PROMPT_CHAT = SystemMessage(content=r"""You are OmniAgent (friendly name: Cherry) — a powerful, offline AI copilot.
You are currently in CHAT MODE.

## BEHAVIOR RULES
1. The user is just chatting, greeting you, or asking a lightweight factual question.
2. Provide a brief, friendly, and conversational response.
3. DO NOT attempt to use or hallucinate any tools. 
4. Keep your response very concise (under 2 paragraphs).
5. Always format your responses using Markdown.
""")

SYSTEM_PROMPT_ACTION = SystemMessage(content=r"""You are OmniAgent (friendly name: Cherry) — an offline autonomous AI copilot running on the user's personal machine.

## 🚨 CRITICAL RULE: NATIVE TOOL CALLING REQUIRED
Whenever the user asks you to perform any physical action, desktop task, browser automation, or search, you MUST select and call the appropriate tool natively.
- NEVER write conversational text explaining how to do it. Call the tool immediately.
- DO NOT pre-announce tool calls (e.g. "I will now use the tool...").

## STRICT GROUNDING RULE
- You are OFFLINE. ALL real-world facts MUST come from tool results.
- When search tools return NO results, you MUST say exactly: "I couldn't find the exact information." NEVER hallucinate facts.

## User Environment Context
- Username: `patlo`. Desktop path is `C:\Users\patlo\Desktop`.

## ReAct Reasoning
1. Write your reasoning inside a `Thought:` block before calling tools.
2. Format output in Markdown.
3. If a tool returns `[NEEDS_APPROVAL:action_key]`, forward that exact token at the top of your response.

## Active Application Context
- Look at the `Active Window Title` and `Current App` in the `[SYSTEM CONTEXT]`.
- If requested to pause/play media on the active tab, use `pause_playback` or `resume_playback`.
- If requested to create a file in an active editor, use `write_file` with `open_in_editor="vscode"` (or notepad).

## Context Tracking
If your action changes the active desktop context, output the updated context in a JSON block at the very end:
```context_state
{
  "current_app": "VS Code",
  "current_directory": "C:\\Users\\patlo\\Desktop",
  "current_file": "cherry"
}
```
Only output keys that have non-null values.
""")

# Define sensitive tools that require approval
SENSITIVE_TOOL_NAMES = {
    "git_commit",
    "write_query",
    "delete_file",
    "execute_shell_command",
    "send_email",
}

def get_active_tools(query: str, history: list) -> list:
    """
    Dynamically filter and select context-relevant tools based on keywords in the
    current query and recent history to prevent local LLMs from getting overwhelmed.
    """
    text = query.lower()
    for msg in history[-4:]:
        if msg.content and isinstance(msg.content, str):
            text += " " + msg.content.lower()

    # Base minimal fallback tools
    active = [open_application, execute_shell_command]

    # File & OS tools
    file_keywords = ["file", "dir", "folder", "read", "write", "create", "delete", "move", "text", "notepad", "vscode", "run", "code"]
    if any(k in text for k in file_keywords):
        active.extend([
            read_file, write_file, delete_file, list_directory, create_directory, search_files,
            open_file_in_vscode, open_folder_in_vscode, run_command_in_vscode_terminal
        ])


    # Git tools
    git_keywords = ["git", "commit", "push", "branch", "checkout", "log", "diff", "status", "repo"]
    if any(k in text for k in git_keywords):
        active.extend([
            git_status,
            git_log,
            git_diff,
            analyze_repo,
            git_commit_and_push,
            git_add,
            git_commit,
            git_checkout,
            git_branch,
        ])

    # SQLite tools
    db_keywords = ["sqlite", "db", "database", "query", "table", "sql", "insert", "select", "update", "delete"]
    if any(k in text for k in db_keywords):
        active.extend([
            read_query,
            write_query,
            list_tables,
            describe_table,
        ])

    # Browser/search tools
    browser_keywords = [
        "browser", "url", "http", "www", "chrome", "edge", "brave",
        "search", "google", "youtube", "play", "video", "music", "song",
        "hotstar", "website", "link", "navigate", "click", "type", "scroll",
        "ipl", "match", "csk", "srh", "tutorial", "find", "web", "tab"
    ]
    if any(k in text for k in browser_keywords):
        active.extend([
            open_url_in_browser,
            search_youtube,
            pause_playback,
            resume_playback,
            web_search,
            research_topic,
            browser_research_and_save,
            youtube_search_and_play,
            browser_navigate,
            browser_click,
            browser_type,
            browser_wait_for,
            browser_take_screenshot,
            browser_close,
            browser_scroll,
            browser_extract_text,
            list_browser_tabs,
            switch_browser_tab,
            scrape_page,
            extract_links,
        ])

    # Email tools
    email_keywords = ["email", "mail", "send", "recipient", "draft", "inbox"]
    if any(k in text for k in email_keywords):
        active.extend([
            send_email,
            send_email_fast,
            save_to_drafts,
            read_emails,
            search_emails,
            research_and_email,
        ])

    # PDF tools
    pdf_keywords = ["pdf", "paper", "document", "read pdf", "summarize pdf"]
    if any(k in text for k in pdf_keywords):
        active.extend([
            extract_pdf_text,
            summarize_pdf,
            extract_pdf_tables,
            split_pdf,
            merge_pdfs,
        ])
    # Job search tools
    job_keywords = ["job", "career", "hiring", "resume", "cv", "apply"]
    if any(k in text for k in job_keywords):
        active.extend([
            analyze_resume_skills,
            save_to_drafts,
            open_url_in_browser,
            web_search,
            research_topic,
        ])
    # Deduplicate and wrap sensitive tools with approval
    seen = set()
    deduped = []
    for tool_obj in active:
        if tool_obj is None:
            continue
        name = getattr(tool_obj, "name", None)
        if not name:
            name = getattr(getattr(tool_obj, "func", None), "__name__", None) or getattr(tool_obj, "__name__", None) or str(tool_obj)
        if name not in seen:
            seen.add(name)
            if name in SENSITIVE_TOOL_NAMES and not getattr(tool_obj, "has_built_in_approval", False) and not hasattr(tool_obj, "_wrapped_by_approval"):
                tool_obj = require_tool_approval(tool_obj)
                setattr(tool_obj, "_wrapped_by_approval", True)
            deduped.append(tool_obj)

    return deduped

llm = ChatOllama(model="llama3.2:latest", temperature=0.1, keep_alive=-1)


def parse_fallback_tool_calls(response):
    # Helper to find balanced JSON blocks
    def find_json_objects(text: str) -> list:
        results = []
        stack = []
        start_idx = -1
        for i, char in enumerate(text):
            if char == '{':
                if not stack:
                    start_idx = i
                stack.append(char)
            elif char == '}':
                if stack:
                    stack.pop()
                    if not stack:
                        results.append(text[start_idx:i+1])
        return results

    # 1. Parse fallback JSON blocks in LLM text output if native tool calls are missing
    if not getattr(response, "tool_calls", None):
        content = getattr(response, "content", "")
        if isinstance(content, str) and '"name"' in content and ('parameters' in content or 'args' in content or 'arguments' in content):
            json_objects = find_json_objects(content)
            for json_str in json_objects:
                try:
                    # Robust backslash escaper for LLMs that output unescaped Windows paths
                    out = []
                    i = 0
                    while i < len(json_str):
                        if json_str[i] == '\\':
                            if i + 1 < len(json_str):
                                nxt = json_str[i+1]
                                if nxt in ['"', '\\', 'n', 'r', 't', 'u']:
                                    out.append('\\')
                                    out.append(nxt)
                                    i += 2
                                else:
                                    out.append('\\')
                                    out.append('\\')
                                    out.append(nxt)
                                    i += 2
                            else:
                                out.append('\\')
                                out.append('\\')
                                i += 1
                        else:
                            out.append(json_str[i])
                            i += 1
                    temp_str = "".join(out)
                    # Fix missing colon or missing quotes after parameters/args if hallucinated
                    import re
                    temp_str = re.sub(r'"(?:parameters|args|arguments)"?\s*:?\s*{', r'"arguments": {', temp_str)
                    
                    tool_data = json.loads(temp_str)
                    if "name" in tool_data and any(k in tool_data for k in ["parameters", "args", "arguments"]):
                        args_data = tool_data.get("parameters") or tool_data.get("args") or tool_data.get("arguments") or {}
                        if isinstance(args_data, str):
                            try:
                                args_data = json.loads(args_data)
                            except:
                                args_data = {}
                        tool_call = {
                            "name": tool_data["name"],
                            "args": args_data,
                            "id": str(uuid.uuid4()),
                            "type": "tool_call"
                        }
                        
                        # Create and return a NEW AIMessage to ensure Pydantic/LangGraph respects the mutation
                        from langchain_core.messages import AIMessage
                        cleaned_content = content.replace(json_str, "").strip()
                        response = AIMessage(
                            content=cleaned_content,
                            tool_calls=[tool_call],
                            id=getattr(response, "id", str(uuid.uuid4()))
                        )
                        break # Only execute the FIRST tool call for sequential turn processing
                except Exception:
                    pass

    # Helper to recursively unpack nested argument dictionaries
    def unpack_args(args_dict):
        if not isinstance(args_dict, dict):
            return args_dict
        unpacked = {}
        for k, v in args_dict.items():
            if k in ("args", "params", "parameters") and isinstance(v, dict):
                unpacked.update(unpack_args(v))
            elif k != "function":
                unpacked[k] = v
        return unpacked

    # 2. Normalize nested params inside tool_calls args (Ollama frequently wraps arguments under 'params' or 'args')
    if getattr(response, "tool_calls", None):
        normalized_calls = []
        for tc in response.tool_calls:
            if isinstance(tc, dict):
                name = tc.get("name", "")
                args = tc.get("args", {})
                args = unpack_args(args)
                if name == "create_directory":
                    if "dirpath" in args:
                        args["path"] = args.pop("dirpath")
                    elif "directory" in args:
                        args["path"] = args.pop("directory")
                tc["args"] = args
                normalized_calls.append(tc)
            else:
                name = getattr(tc, "name", "")
                args = getattr(tc, "args", {})
                unpacked = unpack_args(args)
                if name == "create_directory":
                    if "dirpath" in unpacked:
                        unpacked["path"] = unpacked.pop("dirpath")
                    elif "directory" in unpacked:
                        unpacked["path"] = unpacked.pop("directory")
                setattr(tc, "args", unpacked)
                normalized_calls.append(tc)
        setattr(response, "tool_calls", normalized_calls)

    return response


def call_model(state: AgentState):
    from langchain_core.messages import AIMessage, HumanMessage
    from shared.context import current_session_id, cancel_requests
    
    session_id = current_session_id.get()
    if session_id and session_id in cancel_requests:
        cancel_requests.remove(session_id)
        logger.info("Agent execution stopped by user request for session %s", session_id)
        return {"messages": [AIMessage(content="Generation stopped by user.")]}
        
    messages = list(state.get("messages", []))
    
    # 1. Clean history to keep local models focused and completely block looping
    cleaned_messages = []
    for msg in messages:
        if isinstance(msg, AIMessage) and msg.content:
            content = msg.content
            if isinstance(content, str):
                # Strip markdown code blocks containing json
                content = re.sub(r'```(?:json)?\s*{.*?}\s*```', '', content, flags=re.DOTALL)
                # Strip raw JSON strings
                content = re.sub(r'{[\s\S]*?"name"[\s\S]*?"(?:parameters|args|arguments)"?[\s\S]*?}', '', content)
                # Strip common pre-announcements
                content = re.sub(r'(?i)To answer the question.*?, I will use.*?:', '', content)
                content = re.sub(r'(?i)To get a more accurate understanding.*?, I will use.*?:', '', content)
                content = content.strip()
            cleaned_messages.append(AIMessage(content=content, tool_calls=msg.tool_calls, id=msg.id))
        else:
            cleaned_messages.append(msg)

    is_chat_mode = state.get("is_chat_mode", False)
    base_prompt = SYSTEM_PROMPT_CHAT if is_chat_mode else SYSTEM_PROMPT_ACTION

    if not cleaned_messages or not isinstance(cleaned_messages[0], SystemMessage):
        cleaned_messages = [base_prompt] + cleaned_messages

    # Inject current desktop context
    from services.session_manager import session_manager
    import json
    
    context_state = {}
    if session_id:
        context_state = session_manager.get_session_state(session_id)
    
    system_context_str = f"\n\n[SYSTEM CONTEXT]\nCurrent Desktop Context:\n{json.dumps(context_state, indent=2)}\n"
    
    # We update the SystemMessage content
    if isinstance(cleaned_messages[0], SystemMessage):
        cleaned_messages[0] = SystemMessage(content=cleaned_messages[0].content + system_context_str)
    
    # Get last human message
    last_user_msg = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_msg = msg.content
            break

    if not is_chat_mode:
        # Inject relevant long-term memory and short-term session context
        from services.agent.memory import search_memory, search_session_context
        import time
        from shared.benchmark_logger import log_metric
        t_mem_start = time.perf_counter()
        
        if last_user_msg:
            relevant_memories = search_memory(last_user_msg)
            if relevant_memories and isinstance(cleaned_messages[0], SystemMessage):
                memory_context = f"\n\n## Relevant Long-Term Memories\n{relevant_memories}\n(Use these facts if they are relevant to the user's current query.)\n"
                cleaned_messages[0] = SystemMessage(content=cleaned_messages[0].content + memory_context)

            # Retrieve ongoing "Current Task / Session Window" context via RAG
            if session_id:
                recent_context = search_session_context(session_id, last_user_msg, k=3)
                if recent_context and isinstance(cleaned_messages[0], SystemMessage):
                    session_window = f"\n\n## Current Task Context Window (Retrieved via RAG)\n{recent_context}\n(Use this context to understand what we are doing right now, especially tracking recent fast-path commands.)\n"
                    cleaned_messages[0] = SystemMessage(content=cleaned_messages[0].content + session_window)

        t_mem_end = time.perf_counter()
        log_metric(session_id, "MemoryRetrieval", {"duration": t_mem_end - t_mem_start})

        # Get active tools dynamically based on user message and history
        t_tool_start = time.perf_counter()
        active_tools = get_active_tools(last_user_msg, messages)
        t_tool_end = time.perf_counter()
        
        logger.info("Binding %d active tools to LLM for this turn", len(active_tools))
        llm_with_active_tools = llm.bind_tools(active_tools)
        
        # Calculate approximate token count for tools and messages
        prompt_content = str(cleaned_messages)
        prompt_tokens = len(prompt_content) // 4  # rough estimation
        
        log_metric(session_id, "ToolLoading", {
            "duration": t_tool_end - t_tool_start,
            "tool_count": len(active_tools),
            "tool_names": [getattr(t, "name", str(t)) for t in active_tools],
            "prompt_tokens_estimate": prompt_tokens
        })
    else:
        logger.info("Chat Mode (Mode B): Skipping tool binding and RAG")
        llm_with_active_tools = llm
        
    logger.debug("Agent invoking LLM with %d messages", len(cleaned_messages))
    import time
    from shared.benchmark_logger import log_metric
    t0_llm = time.perf_counter()
    response = llm_with_active_tools.invoke(cleaned_messages)
    t1_llm = time.perf_counter()
    logger.info("LLM pure invoke time: %.3fs", t1_llm - t0_llm)
    log_metric(session_id, "LLMInference", {"duration": t1_llm - t0_llm})
    response = parse_fallback_tool_calls(response)
    
    # 2. Force web_search tool if the LLM lazily forgot to call it for a real-time request
    last_user_msg = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_msg = msg.content
            break
            
    is_realtime_query = any(
        term in last_user_msg.lower()
        for term in ["news", "latest", "weather", "current", "stock", "today", "yesterday", "update", "updates", "right now", "happening"]
    )
    
    # Ensure we only force it on the first turn (before any ToolMessage is received)
    has_tool_responses = any(msg.__class__.__name__ == "ToolMessage" for msg in messages)
    
    if is_realtime_query and not has_tool_responses and not getattr(response, "tool_calls", None):
        logger.info("Real-time query detected. Forcing web_search tool call!")
        import uuid
        tool_call = {
            "name": "web_search",
            "args": {"query": last_user_msg},
            "id": str(uuid.uuid4()),
            "type": "tool_call"
        }
        response = AIMessage(
            content="",
            tool_calls=[tool_call],
            id=getattr(response, "id", str(uuid.uuid4()))
        )
    
    # 3. Format response content (preserve and format thoughts, clean up raw JSON or fluff)
    if response.content:
        content = response.content
        if isinstance(content, str):
            # Parse context_state block
            context_pattern = r"```context_state\s*(\{.*?\})\s*```"
            context_match = re.search(context_pattern, content, re.DOTALL)
            if context_match and session_id:
                try:
                    new_state = json.loads(context_match.group(1))
                    from services.session_manager import session_manager
                    session_manager.update_session_state(session_id, **new_state)
                    # Strip the block from output to keep it clean for user
                    content = content[:context_match.start()] + content[context_match.end():]
                    content = content.strip()
                except Exception as e:
                    logger.error(f"Failed to parse context_state block: {e}")

            # Clean up raw JSON or pre-announcements
            content = re.sub(r'```(?:json)?\s*{.*?}\s*```', '', content, flags=re.DOTALL)
            content = re.sub(r'{[\s\S]*?"name"[\s\S]*?"(?:parameters|args|arguments)"?[\s\S]*?}', '', content)
            content = re.sub(r'(?i)To answer the question.*?, I will use.*?:', '', content)
            content = re.sub(r'(?i)To get a more accurate understanding.*?, I will use.*?:', '', content)
            content = re.sub(r'(?i)^Here is the (?:answer|response).*?:\s*', '', content)
            content = re.sub(r'(?i)^Based on the (?:search )?results.*?:\s*', '', content)
            
            # Override placeholder hallucinations if the small model ignores the system prompt
            if re.search(r'\[insert.*?\]', content, re.IGNORECASE):
                content = "I couldn't find the exact information in the search results."
            else:
                # Clean up ending fluff
                content = re.sub(r'(?i)Note:\s*The response is based on[\s\S]*', '', content).strip()
                
            # Strip literal quotation marks that the LLM sometimes wraps its entire response in
            content = re.sub(r'^["\']|["\']$', '', content.strip())
                
            content = content.strip()

            # Parse and format thoughts using ReAct summary
            thought_pattern = r"(?i)^(?:\*\*?)?Thought(?: Process)?(?:\*\*?)?:\s*(.*?)(?=\n*(?:(?:\*\*?)?(?:Action|Answer|Response|Parameters)(?:\*\*?)?:|$$))"
            thought_match = re.search(thought_pattern, content, re.DOTALL)
            if thought_match:
                thought_text = thought_match.group(1).strip()
                rest_content = content[thought_match.end():].strip()
                rest_content = re.sub(r"(?i)^(?:\*\*?)?(?:Answer|Response)(?:\*\*?)?:\s*", "", rest_content).strip()
                if thought_text:
                    content = f"<details>\n<summary>🧠 Thought Process</summary>\n\n{thought_text}\n</details>\n\n{rest_content}"
            elif getattr(response, "tool_calls", None):
                # If there are tool calls but no explicit thought block, clear content to prevent fluff
                content = ""
            
            # If it's a final response, automatically inject website logo favicons next to all Markdown links!
            if not getattr(response, "tool_calls", None) and content:
                def inject_website_logos(text: str) -> str:
                    import urllib.parse
                    
                    def replacer(match):
                        title = match.group(1)
                        url = match.group(2)
                        if not url.startswith("http"):
                            return match.group(0)
                        try:
                            domain = urllib.parse.urlparse(url).netloc
                            if domain.startswith("www."):
                                domain = domain[4:]
                            if domain:
                                logo_url = f"https://www.google.com/s2/favicons?sz=16&domain={domain}"
                                return f"![logo]({logo_url}) [{title}]({url})"
                        except Exception:
                            pass
                        return match.group(0)
                    
                    pattern = r'(?<!\!)\[([^\]]+)\]\((https?://[^\)]+)\)'
                    return re.sub(pattern, replacer, text)
                    
                content = inject_website_logos(content)
                
            response.content = content.strip()
        
    return {"messages": [response]}


def should_continue(state: AgentState) -> str:
    from shared.context import current_session_id, cancel_requests
    session_id = current_session_id.get()
    if session_id and session_id in cancel_requests:
        return "end"

    messages = state.get("messages", [])
    if not messages:
        return "end"
        
    last_message = messages[-1]
    
    # Tool Validation Layer & Loop Control
    is_chat_mode = state.get("is_chat_mode", False)
    
    tool_iterations = sum(1 for msg in messages if msg.__class__.__name__ == "ToolMessage")
    max_iterations = 0 if is_chat_mode else 1
    
    if getattr(last_message, "tool_calls", None):
        # Validation: If we are in Chat Mode, immediately reject hallucinated tools
        if is_chat_mode:
            logger.warning("Tool Validation: REJECTED tool call %s in Chat Mode", last_message.tool_calls)
            # Remove the hallucinated tool calls to force a final text response instead of routing to action
            last_message.tool_calls = []
            return "end"
            
        # Validation: Limit ReAct Loops
        if tool_iterations >= max_iterations:
            logger.warning("Tool Validation: Max tool iterations reached (%d). Forcing END.", tool_iterations)
            last_message.tool_calls = []
            return "end"
            
        logger.info("Tool Validation: APPROVED tool call %s", last_message.tool_calls)
        return "action"
        
    return "end"


def should_loop(state: AgentState) -> str:
    from shared.context import current_session_id, cancel_requests
    session_id = current_session_id.get()
    if session_id and session_id in cancel_requests:
        return "end"

    messages = state.get("messages", [])
    if messages:
        last_message = messages[-1]
        if last_message.__class__.__name__ == "ToolMessage" and "[NEEDS_APPROVAL:" in str(last_message.content):
            logger.info("Pending approval request detected in tool output. Pausing graph execution.")
            return "end"
    return "agent"


workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)

original_tool_node = ToolNode(all_combined_tools)

def benchmarked_tool_node(state: AgentState):
    import time
    from shared.benchmark_logger import log_metric
    from shared.context import current_session_id
    
    session_id = current_session_id.get()
    t_start = time.perf_counter()
    result = original_tool_node.invoke(state)
    t_end = time.perf_counter()
    
    messages = state.get("messages", [])
    tool_calls = getattr(messages[-1], "tool_calls", []) if messages else []
    tool_names = [tc.get("name") for tc in tool_calls if isinstance(tc, dict)]
    
    log_metric(session_id, "ToolExecution", {
        "duration": t_end - t_start,
        "tools_called": tool_names
    })
    return result

workflow.add_node("action", benchmarked_tool_node)
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, {"action": "action", "end": END})
workflow.add_conditional_edges("action", should_loop, {"agent": "agent", "end": END})
app = workflow.compile()
