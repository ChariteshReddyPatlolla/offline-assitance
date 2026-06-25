from typing import Any, Dict
from .base_agent import BaseAgent
from ..interfaces.llm_provider import ILLMProvider

class EmailAgent(BaseAgent):
    """
    Agent responsible for email operations: drafting, sending, reading, searching, and handling attachments.
    """
    def __init__(self, llm_provider: ILLMProvider):
        super().__init__(name="email_agent", llm_provider=llm_provider)
        self._capabilities = ["email_drafting", "email_sending", "email_reading", "email_searching"]

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process email-related tasks and decide on the next action or node.
        """
        latest_message = state["messages"][-1].get("content", "") if state.get("messages") else ""
        
        system_prompt = f"""
        You are the Email Agent. Your job is to manage email-related tasks.
        If the user wants to send an email, use the 'send_email' tool (which will trigger an approval prompt).
        If the user wants to only draft an email without sending, use 'save_to_drafts' to save it to their IMAP Drafts folder.
        If the user wants to read or search emails, use 'read_emails' or 'search_emails'.
        
        Analyze the user's intent and execute the necessary steps.
        If the email task is complete or you need to return control to the user, output "END".
        Otherwise, output your reasoning and tool calls.
        """
        
        response = await self._llm_provider.generate(prompt=latest_message, system_prompt=system_prompt)
        
        if response.strip() == "END":
            return {"next_node": "END", "current_agent": self.get_name(), "messages": state.get("messages", [])}
            
        return {
            "next_node": "executor_agent",
            "current_agent": self.get_name(),
            "messages": state.get("messages", []) + [{"role": "assistant", "content": response}]
        }
