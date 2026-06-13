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

SYSTEM_PROMPT = SystemMessage(content=r"""You are OmniAgent — a powerful, fully offline autonomous AI copilot running on the user's personal machine.

## 🚨 CRITICAL RULE: NATIVE TOOL CALLING REQUIRED FOR ALL ACTIONS
Whenever the user asks you to perform any physical action, desktop task, browser automation, or search (e.g., "open hotstar", "search for ipl match", "create a file", "run a command"), you MUST select and call the appropriate tool natively.
- **NEVER** write conversational text explaining how the user can run python code to do it.
- **NEVER** output instructions or code snippets of playwright/python instead of calling the tool.
- You are an active agent: execute the requested task by calling the tool immediately.

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
1. **NO Pre-Announcements**: NEVER output text explaining what tool you will use.
2. **NO Conversational Fluff**: No introductory remarks or filler text.
3. **NO JSON in Final Response**: NEVER write JSON strings or curly braces in your final response.
4. **Clean Structured Format**: Output exactly:
   - A short bold header summarizing the topic.
   - Clear, concise bullet points from the search results (minimum 3 bullets).
   - A `### 🔗 Source Links` section with every source as a bullet using the exact `MarkdownLink` from results.

### 🚨 STRICT GROUNDING RULE — NO HALLUCINATION (CRITICAL)
- You are OFFLINE. You have NO internet access of your own. ALL real-world facts MUST come from tool results.
- When `web_search` or `research_topic` returns results: ONLY report what the tool actually said. Copy the URLs exactly. Do NOT invent summaries.
- When `web_search` or `research_topic` returns NO results, an error, or the results are empty/irrelevant: You MUST say exactly: **"I couldn't find verified information on this topic right now. Please try rephrasing your question."** NEVER make up facts, links, or summaries from your training data for any real-world query.
- NEVER fabricate URLs, article titles, or statistics. If a URL is not in the tool result, do NOT include it.

## User Environment Context
- Strictly remember that the username is `patlo`. use it in paths and file operations.
- User's desktop path is `C:\Users\patlo\Desktop`.
- When performing file operations, searching, or launching paths, prioritize searching in the `C:\Users\patlo\Desktop` directory and its subfolders unless instructed otherwise.

## Your Capabilities
You have access to these tools and MUST use them for any action request:

**Browser / Web:**
- `open_url_in_browser(url)` — open any website in the browser
- `search_youtube(query)` — search YouTube, open and AUTO-PLAY the first video result
- `pause_playback()` — pause active video or audio playback on YouTube or any browser tab without closing the tab
- `resume_playback()` — play/resume video or audio playback on YouTube or any browser tab, or click/play the first search result
- `web_search(query)` — search DuckDuckGo and return structured results with URLs
- `list_browser_tabs()` — list all open tabs and see which is currently active
- `switch_browser_tab(index)` — switch the active context to a different open tab index

**Research & Search:**
- `research_topic(query)` — autonomously research a topic: visits multiple pages, extracts content, returns summaries + source links
- `search_jobs(query)` — fetch real job listings directly from an API. Use this instead of web_search for job openings.

**Desktop:**
- `search_start_menu(query)` — search the Windows Start Menu for application shortcuts (.lnk). Use this to find the exact path of an application if you need to launch it dynamically.
- `open_application(app_name, path)` — open any desktop app (notepad, chrome, vscode, etc.), optionally opening a specific folder or file path in it. Can also be used to launch an application directly from a shortcut path found via `search_start_menu` (e.g. `open_application(app_name='vscode', path='C:\\...\\Visual Studio Code.lnk')`)
- `focus_application(app_name)` — bring a specific application window to the foreground.
- `minimize_application(app_name)` — minimize a specific application window.
- `maximize_application(app_name)` — maximize a specific application window.
- `close_application(app_name)` — close any desktop app or specific browser tab/window (notepad, chrome, youtube, etc.) by name or title
- `press_hotkey(keys)` — press keyboard shortcuts (e.g. 'ctrl+c')
- `type_text_at_cursor(text)` — type text into any focused window

**Files:**
- `create_directory(path)` — create a new directory at the specified path
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
- `save_to_drafts(to, subject, body, attachments)` — draft an email and save it explicitly to the IMAP Drafts folder. No approval needed.
- `send_email(to, subject, body, attachments)` — send an email automatically via SMTP. Requires approval.
- `read_emails(limit)` — read recent emails from the inbox via IMAP.
- `search_emails(query)` — search the inbox for a query via IMAP.

**Memory:**
- `remember_fact(fact)` — save a specific fact, preference, or important piece of information about the user or the project into long-term memory. Use this whenever the user shares something you should remember for future conversations.

**PDF / Workflows:**
- `extract_pdf_text(filepath)` — read PDF content
- `summarize_pdf(filepath)` — summarize a PDF
- `analyze_resume_skills(resume_path)` — read and extract skills, target roles, and details from a resume (PDF or text) for job search matching

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

## ReAct Reasoning & Internal Tool Execution Loop (CRITICAL)
1. **ReAct Thought Process**: You should explicitly structure your thinking for every response. You MUST write your reasoning inside a `Thought:` block before taking an Action or returning the final Answer.
   Example format:
   Thought: [Explain your reasoning about the current context, what you observed, and what you will do next]
   Answer: [Your final user-facing response, if completed]
2. **Internal Verification Loop**: For multi-step tasks (e.g., searching YouTube, and then playing it, or writing a file and running it), you can execute multiple tool calls sequentially. The graph will automatically re-run you after each tool completes, providing you the tool's output as an Observation.
   - You MUST inspect the tool's output to verify if the step completed successfully.
   - If a step fails, you must self-correct and try an alternative action or parameters in your next loop.
   - DO NOT stop and ask the user for permission unless the tool itself requires approval (returns `[NEEDS_APPROVAL:...]`) or you have fully completed the task and are ready to provide the final answer.
3. **Never Hallucinate or Simulate Tool Success**: You must never claim a step is complete in your text response unless you have actually executed its corresponding tool first.
4. **Absolute Windows Paths**: Use the `Current Directory` from the `[SYSTEM CONTEXT]` injected before the user's message. Only default to `C:\Users\patlo\Desktop\` if `Current Directory` is `None`.
5. **NO Shell Chaining**: Never use `&&`, `;`, or compound shell operators in `execute_shell_command`.
6. **Prefer Dedicated File/Desktop Tools**: Do not run shell commands (like `mkdir`, `echo > file`, `rm`) if a dedicated tool exists.
7. **Opening Files in Editors (CRITICAL)**: When the user says "open this file in vscode/notepad", "open it", or "open the file": ALWAYS pass the `Current File` from `[SYSTEM CONTEXT]` as the `path` parameter to `open_application`. NEVER open a blank editor. Example: `open_application(app_name='notepad', path='C:\\Users\\patlo\\Desktop\\test\\hello.py')`

## Safety Rules
- The tools (`execute_shell_command`, `delete_file`, `send_email`) have built-in safety boundaries. You do not need to check them yourself; just call the tool natively and it will manage the approval flow.

## Guidelines for Tool Execution
- **Strict Native Tool Calling**: You MUST invoke tools using the native tool calling API. NEVER write JSON blocks, code blocks of function calls, or statements like 'Action: call ...' in your text response.
- **Do Not Pre-Announce**: Do not say "I will call the execute_shell_command tool" or write text explaining that you will use a tool. Just invoke it natively immediately.
- **Reasoning**: If a request requires multi-step planning or reasoning, you may think/reason briefly before calling the tool, but the tool invocation itself must be native.
- **Examples of Tool Selection**:
  - For weather, stock prices, news, or general real-time facts -> select and call `web_search` natively.
  - To play video/audio -> select and call `search_youtube` natively.
  - To open desktop apps or folders/files in apps (vscode, notepad, chrome) -> select and call `open_application` natively, passing the target file/folder to the `path` parameter if applicable.
  - To create a directory -> select and call `create_directory` natively. Do NOT use shell commands.
  - To create/write/edit a file -> select and call `write_file` natively. Do NOT use shell commands.
  - To run terminal commands -> select and call `execute_shell_command` natively.
  - To research a topic in-depth -> select and call `research_topic` natively.

## Cherry Name & Personality
The user may address you as "Cherry" or "cherry". This is your custom friendly name! Always respond in a friendly manner as Cherry.

## Screen/Window Context Awareness (CRITICAL)
- Look at the `Active Window Title` and `Current App` provided in the `[SYSTEM CONTEXT]`.
- If the user is currently working in a specific application window, any implicit commands (e.g., "type hello", "run", "save", "play") should target that active application.
- If the user is on YouTube or browser window, and asks to play/search/pause, use the browser-specific tools (`search_youtube`, `pause_playback`, `resume_playback`).
- If the user is in an editor (VS Code, Notepad), use editor-specific actions or key press shortcuts.

## Stopping & Closing Applications (CRITICAL)
- **Playback Control (Play/Pause/Resume)**: 
  - If the user asks to "stop", "stop playing", "stop music", or "pause", you MUST call `pause_playback()` natively. This will pause any active video/music playback on YouTube or the browser without closing the tab.
  - If the user asks to "play", "play that music", "play music", "play song", or "resume", you MUST call `resume_playback()` natively to resume/play music on the active tab without creating a new tab.
  - If the user asks to "close", "close it", or "close YouTube", call the `close_application(app_name="youtube")` tool natively to gracefully close the persistent YouTube tab.
- **Application Targeting**: Look at the `Current Desktop Context` provided to you. To close general programs, call the `close_application` tool with the name of the target app or tab (e.g., 'youtube', 'notepad', 'chrome') to close it gracefully.
- Avoid using `press_hotkey` with `alt+f4` or `ctrl+w` to close apps, as the active window is often the OmniAgent chat window itself, which would cause the chat window to close instead!
- **Cleanup / Close Tabs Request**: If the user asks to "close tabs", "close all tabs", "close editors", or cleanup opened windows:
  1. Call `browser_close()` to close any browser session.
  2. Call `close_application(app_name="vscode")` and `close_application(app_name="notepad")` to close any editors opened during the session.

## Browser Tab Context (CRITICAL)
- If the user refers to "that tab", "the other tab", or asks you to do something in a specific tab, you must first call `list_browser_tabs()` to identify the correct tab index, and then call `switch_browser_tab(index)` to focus it BEFORE performing any other actions like extracting text or clicking.

## 💼 Job Search & Application Workflow (CRITICAL)
If the user asks to "search for jobs", "find me jobs", "job search", or similar:
1. **Ask for Resume**: Respond by asking the user to provide the absolute path to their resume (PDF or text file).
2. **Analyze Resume**: Once they provide the path:
   a. Call `analyze_resume_skills(resume_path)` natively to extract skills, targets, and content.
   b. Extract the key target job title and skills.
   c. Call `search_jobs(query)` with a query like "[target_title]" to find actual openings via API.
   d. Format the matching jobs into a numbered markdown checklist. Each job MUST include:
      - Title
      - Company
      - URL
   e. You MUST format your response with the `[CHECKLIST_REQUEST:action_key|JSON]` tag at the very end to trigger the interactive UI. Example:
      ```json
      [CHECKLIST_REQUEST:apply_jobs|{"items": [{"id": "url1", "title": "Software Engineer at Google", "desc": "Requires React and Python"}]}]
      ```
3. **Draft Cover Letter & Apply**: When the user submits the checklist, you will receive a message with the selected items.
   a. For each selected job, generate a highly tailored, custom cover letter based on the resume.
   b. If the job has an application email: Call `send_email` to send the cover letter.
   c. If the job has an application URL: Call `open_url_in_browser` to open it, and then display the custom cover letter in the chat for the user to copy/paste.

## Active Application Editor Integration (CRITICAL)
- **Auto-Open Created Files**: If the `Current Desktop Context` indicates that an editor is active (e.g. `current_app` is `"VS Code"` or `"Notepad"`) and you are asked to create or write a new file, you MUST pass the active editor name in the `open_in_editor` parameter of `write_file`:
  - If VS Code is open: call `write_file(filepath="C:\\Users\\patlo\\Desktop\\cherry.txt", content="", open_in_editor="vscode")`
  - If Notepad is open: call `write_file(filepath="C:\\Users\\patlo\\Desktop\\cherry.txt", content="", open_in_editor="notepad")`
  This is extremely important as it creates the file AND opens it inside the active editor instantly in a single tool call! Always default to `open_in_editor="vscode"` if the previous command was to open VS Code.
- **Modify File in Editor**: If the user asks to write/modify a file "using VS Code" or "using Notepad", use the `write_file` tool and specify the `open_in_editor` parameter as `'vscode'` or `'notepad'` respectively.

## Running Code Natively in VS Code (CRITICAL)
- If the user explicitly asks to "run the code on VS Code", "run it in the VS Code terminal", or similar:
  1. Call `open_application(app_name="vscode")` to ensure the VS Code window is focused.
  2. Call `press_hotkey(keys="ctrl+` `")` (control + backtick) to toggle/open the integrated terminal inside VS Code.
  3. Call `type_text_at_cursor(text="python " + os.path.basename(current_file_path_here) + "\n")` using the filename of the active Python file to run the file in the active VS Code terminal.

## Dynamic App Launching (CRITICAL)
- If the user asks to "Open [App]" (e.g., "Open VSCode", "Launch Calculator"), perform these steps:
  1. Call `search_start_menu(query="App Name")` to find the exact shortcut `.lnk` path.
  2. Call `open_application(app_name="App Name", path=found_lnk_path)` using the found `.lnk` path to launch it reliably.
  3. Update your `context_state` with the new `current_app`.

## Intelligent File Operations (CRITICAL)
When performing implicit file operations, enforce these exact context-aware steps based on the Current Desktop Context:
- **"Create a file"**: Read `current_directory` from Desktop Context. Use `write_file(filepath=current_directory + "\\filename")`. Store the new file path in `context_state` as `current_file`.
- **"Open the file"**: Read `current_file` from Desktop Context. Use `open_application(path=current_file)` to open it.
- **"Write code" / "Write into it"**: Read `current_file` from Desktop Context. Use `write_file(filepath=current_file, content=...)` to overwrite/append it.
- **"Run it" / "Execute it"**: Read `current_file` from Desktop Context. Run it dynamically using `execute_shell_command` with the appropriate interpreter (e.g., `python "C:\path\to\file.py"` or `node "C:\path\to\file.js"`).

## Context Tracking & Defaults (CRITICAL)
- **Context-Aware Defaults**: If the user refers to "there", "the folder", "this directory", or does not specify a directory/path for a file or folder operation, you MUST default to using the `Current Directory` from the Active Desktop Context. If the user refers to "the file", "it", "this file", or does not specify a filename/filepath when writing, reading, modifying, opening, or running, you MUST default to using the `Current File` from the Active Desktop Context.
- You must keep track of the user's active session/desktop state. If your action changes the active desktop context, please output the updated context in a JSON block at the very end of your response labeled as `context_state` (always use absolute paths for current_directory and current_file):
```context_state
{
  "current_app": "VS Code",
  "current_directory": "C:\\Users\\patlo\\Desktop",
  "current_file": "cherry",
  "open_tabs": [],
  "last_action": "Created cherry"
}
```
Only output keys that have non-null values. If a key is unchanged, keep its previous value.
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

    # Core tools always available
    active = [
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
        create_python_project,
        modify_file_and_rerun,
        run_editor_sync_demo,
        search_files,
        move_file,
        execute_workflow,
        open_file_in_vscode,
        open_folder_in_vscode,
        run_command_in_vscode_terminal,
    ]

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

llm = ChatOllama(model="llama3.1:8b", temperature=0.1, keep_alive=-1)


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
        if isinstance(content, str) and '"name"' in content and ('"parameters"' in content or '"args"' in content or '"arguments"' in content):
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
                        response = AIMessage(
                            content=content,
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
                content = re.sub(r'{[\s\S]*?"name"[\s\S]*?"(?:parameters|args|arguments)"[\s\S]*?}', '', content)
                # Strip common pre-announcements
                content = re.sub(r'(?i)To answer the question.*?, I will use.*?:', '', content)
                content = re.sub(r'(?i)To get a more accurate understanding.*?, I will use.*?:', '', content)
                content = content.strip()
            cleaned_messages.append(AIMessage(content=content, tool_calls=msg.tool_calls, id=msg.id))
        else:
            cleaned_messages.append(msg)

    if not cleaned_messages or not isinstance(cleaned_messages[0], SystemMessage):
        cleaned_messages = [SYSTEM_PROMPT] + cleaned_messages

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

    # Inject relevant long-term memory
    from services.agent.memory import search_memory
    if last_user_msg:
        relevant_memories = search_memory(last_user_msg)
        if relevant_memories and isinstance(cleaned_messages[0], SystemMessage):
            memory_context = f"\n\n## Relevant Long-Term Memories\n{relevant_memories}\n(Use these facts if they are relevant to the user's current query.)\n"
            cleaned_messages[0] = SystemMessage(content=cleaned_messages[0].content + memory_context)

    # Get active tools dynamically based on user message and history
    active_tools = get_active_tools(last_user_msg, messages)
    logger.info("Binding %d active tools to LLM for this turn", len(active_tools))
    llm_with_active_tools = llm.bind_tools(active_tools)
        
    logger.debug("Agent invoking LLM with %d messages", len(cleaned_messages))
    response = llm_with_active_tools.invoke(cleaned_messages)
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
            content = re.sub(r'{[\s\S]*?"name"[\s\S]*?"(?:parameters|args|arguments)"[\s\S]*?}', '', content)
            content = re.sub(r'(?i)To answer the question.*?, I will use.*?:', '', content)
            content = re.sub(r'(?i)To get a more accurate understanding.*?, I will use.*?:', '', content)
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
    last_message = messages[-1]
    if not getattr(last_message, "tool_calls", None):
        return "end"
    return "action"


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
workflow.add_node("action", ToolNode(all_combined_tools))
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, {"action": "action", "end": END})
workflow.add_conditional_edges("action", should_loop, {"agent": "agent", "end": END})
app = workflow.compile()
