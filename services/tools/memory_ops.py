from langchain_core.tools import tool
from services.agent.memory import add_memory

@tool
def remember_fact(fact: str) -> str:
    """
    Saves a specific fact, preference, or important piece of information about the user or the project into long-term memory.
    Use this whenever the user shares something you should remember for future conversations (e.g., "My favorite color is blue", "I'm working on a React project").
    """
    success = add_memory(fact)
    if success:
        return f"Successfully remembered: {fact}"
    else:
        return f"Failed to remember: {fact}"
