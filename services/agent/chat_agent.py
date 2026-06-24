# services/agent/chat_agent.py

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

# Import all tools
from services.tools import all_tools as tools

# Local Ollama model
llm = ChatOllama(
    model="llama3.2:latest",
    temperature=0.2,   # Lower temperature improves tool-calling reliability
    keep_alive=-1      # Keep model loaded in memory indefinitely
)

# Strong system prompt to force tool usage
SYSTEM_PROMPT = """
You are OmniAgent, a highly capable private offline AI copilot.

Your primary goal is to COMPLETE the user's request using the available tools.

GENERAL RULES:
1. If a tool can answer the user's request, you MUST use the tool.
2. Do NOT tell the user to visit websites or do tasks manually when a tool can do it.
3. Prefer actions over explanations.
4. You may use multiple tools in sequence.
5. Continue until the task is fully completed.
6. Only ask clarifying questions when essential information is missing.
7. After using tools, provide a concise final answer.

WHEN TO USE TOOLS:
- Current information (weather, news, prices, facts) -> web_search
- Deep Web Automation -> You can fully control the browser! Use `browser_navigate`, `browser_click`, `browser_type`, `browser_extract_text`, `browser_wait_for`, and `browser_close` to interact with complex web apps (like Overleaf, GitHub). You can read the screen, click buttons, type code into web IDEs, and re-run code automatically!
- Open websites (simple) -> open_url_in_browser
- Play videos/music -> search_youtube
- Open installed applications -> open_application
- Read/write/delete/list files -> file tools
- Write code in VS Code -> Use `write_file` to generate the code, then use `open_file_in_vscode` to visually pop it open for the user.
- Execute terminal commands -> execute_shell_command
- Git repository analysis -> git_status, git_log, git_diff, analyze_repo
- PDF extraction/summarization -> extract_pdf_text, summarize_pdf
- Research topics -> research_topic
- Draft emails -> draft_email
- Desktop automation -> screenshot, typing, hotkeys
"""

# Create autonomous ReAct agent
agent = create_react_agent(
    llm,
    tools,
)

def generate_response(new_message: str, past_messages: list) -> str:
    """
    Generates a response using the LangGraph ReAct agent with tool support.
    """

    messages = [SystemMessage(content=SYSTEM_PROMPT)]

    # Add conversation history
    for msg in past_messages:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            messages.append(AIMessage(content=msg.content))

    # Add latest user message if not already present
    if (
        not past_messages
        or past_messages[-1].role != "user"
        or past_messages[-1].content != new_message
    ):
        messages.append(HumanMessage(content=new_message))

    # Invoke the agent
    result = agent.invoke(
        {
            "messages": messages
        }
    )

    # Return the final assistant message
    return result["messages"][-1].content