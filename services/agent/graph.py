import re
import json
import uuid
import logging
from langgraph.graph import StateGraph, START, END
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage,AIMessage,HumanMessage
from langgraph.prebuilt import ToolNode
from services.agent.state import AgentState
from services.tools import all_tools

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = SystemMessage(content="""You are OmniAgent — a powerful, fully offline autonomous AI copilot running on the user's personal machine.

## Response Formatting
ALWAYS format your responses using Markdown:
- Use **bold** for emphasis and key terms
- Use `code blocks` for commands, code, and file paths
- Use bullet points and numbered lists for steps
- Use headings (## ###) to organize longer responses
- Use > blockquotes for important notes
- Include code blocks with language hints: ```python, ```bash, etc.
- Make your output look like Claude or ChatGPT — structured and readable

### 🚨 Strict Search & News Response Rule (CRITICAL)
When the user asks for news, current events, weather, stock prices, or any other topic requiring web searches:
1. **NO Pre-Announcements**: NEVER output text explaining what tool you will use, e.g. do NOT say "To answer the question, I will use...", "Based on the search results...", or "I will perform a web search...".
2. **NO Conversational Fluff**: Do NOT output introductory remarks, filler text, or conversational preambles.
3. **NO JSON in Final Response**: NEVER write or show JSON strings, tool formats, or curly braces in your final response to the user.
4. **Clean Structured Format**: Output exactly:
   - A short bold header summarizing the topic (e.g. **Latest News on SpaceX Starship**).
   - Clear, concise bullet points synthesizing the key news facts found in the search results (minimum 3 bullet points).
   - A dedicated `### 🔗 Source Links` section where every source is listed as a bullet point containing the exact `MarkdownLink` provided in the search results (e.g. `* [MarkdownLink]`). Do NOT format it yourself — copy-paste the exact `MarkdownLink` value provided!

## Your Capabilities
You have access to these tools and MUST use them for any action request:

**Browser / Web:**
- `open_url_in_browser(url)` — open any website in the browser
- `search_youtube(query)` — search YouTube, open and AUTO-PLAY the first video result
- `web_search(query)` — search DuckDuckGo and return structured results with URLs

**Research:**
- `research_topic(query)` — autonomously research a topic: visits multiple pages, extracts content, returns summaries + source links

**Desktop:**
- `open_application(app_name)` — open any desktop app (notepad, chrome, vscode, etc.)
- `press_hotkey(keys)` — press keyboard shortcuts (e.g. 'ctrl+c')
- `type_text_at_cursor(text)` — type text into any focused window

**Files:**
- `read_file(filepath)` — read any file
- `write_file(filepath, content)` — write/edit files
- `delete_file(filepath)` — delete a file
- `list_directory(dirpath)` — list directory contents

**Shell:**
- `execute_shell_command(command)` — run terminal commands

**Git:**
- `git_status(repo_path)` — check git status
- `git_log(repo_path, n)` — view commit history
- `git_diff(repo_path)` — view changes
- `analyze_repo(repo_path)` — full repo analysis

**Email:**
- `draft_email(to, subject, body)` — draft and send an email automatically

**PDF:**
- `extract_pdf_text(filepath)` — read PDF content
- `summarize_pdf(filepath)` — summarize a PDF

## Behavior Rules
1. **Always call the tool first**: For any action (deleting a file, running a shell command, writing a file, sending an email, or searching the web), you MUST invoke the tool natively. NEVER try to decide if it needs approval yourself.
2. **NEVER pre-emptively ask for approval**: Do not write approval text, warnings, or `[NEEDS_APPROVAL:...]` tokens yourself. The tool contains all the safety logic and will generate the approval request if needed.
3. **Forward Tool Approvals**: If a tool returns a `[NEEDS_APPROVAL:action_key]` token in its output, you MUST simply forward that exact token `[NEEDS_APPROVAL:action_key]` at the very top of your text response so the system can display the Yes/No buttons. Do not try to bypass or re-run the tool until the user clicks Approve.
4. **Be concise**: Confirm completed actions briefly. Don't over-explain.
5. **YouTube/music**: Use `search_youtube` immediately — don't ask for confirmation. It auto-plays the first video.
6. **Research**: Use `research_topic` for any research request — it visits multiple pages.
7. **Format output**: Always use markdown. Never send plain unformatted text for multi-line responses.
8. **Real-Time Queries & News**: For ANY query requiring up-to-date information (weather, stock prices, news, latest papers, current events), you MUST use the `web_search` tool immediately. Do not rely on internal knowledge.
9. **Formatting Search Results**: When answering news, current events, or search queries, you MUST synthesize the results and answer using clear **bullet points** and **always include clickable Markdown reference links** (e.g. `[Source Title](URL)`) pointing to the source URLs of the information!

## Safety Rules
- The tools (`execute_shell_command`, `delete_file`, `write_file`, `draft_email`) have built-in safety boundaries. You do not need to check them yourself; just call the tool natively and it will manage the approval flow.

## Guidelines for Tool Execution
- **Strict Native Tool Calling**: You MUST invoke tools using the native tool calling API. NEVER write JSON blocks, code blocks of function calls, or statements like 'Action: call ...' in your text response.
- **Do Not Pre-Announce**: Do not say "I will call the execute_shell_command tool" or write text explaining that you will use a tool. Just invoke it natively immediately.
- **Reasoning**: If a request requires multi-step planning or reasoning, you may think/reason briefly before calling the tool, but the tool invocation itself must be native.
- **Examples of Tool Selection**:
  - For weather, stock prices, news, or general real-time facts -> select and call `web_search` natively.
  - To play video/audio -> select and call `search_youtube` natively.
  - To open desktop apps (notepad, chrome, vscode) -> select and call `open_application` natively.
  - To run terminal commands -> select and call `execute_shell_command` natively.
  - To research a topic in-depth -> select and call `research_topic` natively.
""")

llm = ChatOllama(model="llama3.1:8b", temperature=0.1)
llm_with_tools = llm.bind_tools(all_tools)


def parse_fallback_tool_calls(response):
    if getattr(response, "tool_calls", None):
        return response
    
    content = getattr(response, "content", "")
    if isinstance(content, str) and '"name"' in content and '"parameters"' in content:
        match = re.search(r'```(?:json)?\s*({.*?})\s*```', content, re.DOTALL)
        if not match:
            match = re.search(r'({[\s\S]*?"name"[\s\S]*?"parameters"[\s\S]*?})', content)
        
        if match:
            try:
                # Escape single backslashes for Windows paths so json.loads doesn't crash
                json_str = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', match.group(1))
                tool_data = json.loads(json_str)
                if "name" in tool_data and "parameters" in tool_data:
                    tool_call = {
                        "name": tool_data["name"],
                        "args": tool_data["parameters"],
                        "id": str(uuid.uuid4()),
                        "type": "tool_call"
                    }
                    
                    # Create and return a NEW AIMessage to ensure Pydantic/LangGraph respects the mutation
                    from langchain_core.messages import AIMessage
                    return AIMessage(
                        content=content,
                        tool_calls=[tool_call],
                        id=getattr(response, "id", str(uuid.uuid4()))
                    )
            except Exception:
                pass
    return response


def call_model(state: AgentState):
    from langchain_core.messages import AIMessage, HumanMessage
    
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
                content = re.sub(r'{[\s\S]*?"name"[\s\S]*?"parameters"[\s\S]*?}', '', content)
                # Strip common pre-announcements
                content = re.sub(r'(?i)To answer the question.*?, I will use.*?:', '', content)
                content = re.sub(r'(?i)To get a more accurate understanding.*?, I will use.*?:', '', content)
                content = content.strip()
            cleaned_messages.append(AIMessage(content=content, tool_calls=msg.tool_calls, id=msg.id))
        else:
            cleaned_messages.append(msg)

    if not cleaned_messages or not isinstance(cleaned_messages[0], SystemMessage):
        cleaned_messages = [SYSTEM_PROMPT] + cleaned_messages
        
    logger.debug("Agent invoking LLM with %d messages", len(cleaned_messages))
    response = llm_with_tools.invoke(cleaned_messages)
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
    
    # 3. If it's a tool-calling turn, strip JSON text or pre-announcements from final content
    # so the frontend user never sees raw JSON or fluff when the tool executes!
    if getattr(response, "tool_calls", None) and response.content:
        content = response.content
        if isinstance(content, str):
            content = re.sub(r'```(?:json)?\s*{.*?}\s*```', '', content, flags=re.DOTALL)
            content = re.sub(r'{[\s\S]*?"name"[\s\S]*?"parameters"[\s\S]*?}', '', content)
            content = re.sub(r'(?i)To answer the question.*?, I will use.*?:', '', content)
            content = re.sub(r'(?i)To get a more accurate understanding.*?, I will use.*?:', '', content)
            content = content.strip()
        response.content = content
    elif not getattr(response, "tool_calls", None) and response.content:
        # If it's a final response, automatically inject website logo favicons next to all Markdown links!
        content = response.content
        if isinstance(content, str):
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
                
                # Match [Title](URL) but ensure it is not already an image ![logo](url)
                pattern = r'(?<!\!)\[([^\]]+)\]\((https?://[^\)]+)\)'
                return re.sub(pattern, replacer, text)
                
            content = inject_website_logos(content)
        response.content = content
        
    return {"messages": [response]}


def should_continue(state: AgentState) -> str:
    messages = state.get("messages", [])
    last_message = messages[-1]
    if not getattr(last_message, "tool_calls", None):
        return "end"
    return "action"


workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("action", ToolNode(all_tools))
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, {"action": "action", "end": END})
workflow.add_edge("action", "agent")
app = workflow.compile()
