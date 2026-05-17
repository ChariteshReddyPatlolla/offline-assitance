from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Using the llama3.1:8b model which the user has installed
llm = ChatOllama(model="llama3.1:8b", temperature=0.7)

def generate_response(new_message: str, past_messages: list) -> str:
    messages = [
        SystemMessage(content="You are OmniAgent, a highly capable, private, offline AI copilot. Provide concise and accurate answers.")
    ]
    
    # Add history
    for msg in past_messages:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            messages.append(AIMessage(content=msg.content))
            
    # Add new message (note: if past_messages already includes new_message, we skip this, 
    # but in our api route we saved the user message to db before calling this, so it's in past_messages)
    # Wait, in the api route we added it to DB, so it is in past_messages!
    
    response = llm.invoke(messages)
    return response.content
