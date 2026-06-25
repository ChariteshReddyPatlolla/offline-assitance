import asyncio
import logging
import requests
import json

logger = logging.getLogger(__name__)

class AntigravityController:
    """
    Manages communication with the Antigravity system via its REST API.
    """
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.is_open = False
        self.session_id = "auto_worker_session"
        self.user_id = "orchestrator_bot"

    async def open_antigravity(self) -> bool:
        """Launches the Antigravity worker environment."""
        logger.info("Opening Antigravity API connection...")
        self.is_open = True
        return self.is_open

    async def send_prompt(self, prompt: str) -> str:
        """Sends a prompt to Antigravity and waits for the final response."""
        if not self.is_open:
            raise RuntimeError("Antigravity is not open.")
        
        logger.info(f"Sending prompt to Antigravity: {prompt[:50]}...")
        
        def _post():
            return requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "session_id": self.session_id,
                    "user_id": self.user_id,
                    "message": prompt
                },
                timeout=120
            )
            
        response = await asyncio.to_thread(_post)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error from Antigravity: {response.text}")
            return {"content": f"Error: {response.text}"}

    async def get_pending_approvals(self) -> list:
        """Gets currently pending approvals for the worker session."""
        def _get():
            return requests.get(f"{self.base_url}/api/approvals/pending/{self.session_id}", timeout=10)
            
        try:
            response = await asyncio.to_thread(_get)
            if response.status_code == 200:
                return response.json().get("pending", [])
        except Exception as e:
            logger.warning(f"Failed to fetch approvals: {e}")
        return []

    async def decide_approval(self, action_key: str, approved: bool) -> bool:
        """Programmatically clicks Yes (approved=True) or No (approved=False)."""
        def _post():
            return requests.post(
                f"{self.base_url}/api/approvals/decide",
                json={
                    "session_id": self.session_id,
                    "action_key": action_key,
                    "approved": approved
                },
                timeout=120
            )
            
        logger.info(f"Deciding approval for {action_key}: {'YES' if approved else 'NO'}")
        try:
            response = await asyncio.to_thread(_post)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to decide approval: {e}")
            return False

    async def read_response(self) -> str:
        """Legacy stub - prompt response is now returned directly from send_prompt"""
        return ""

    async def close_antigravity(self):
        """Closes the Antigravity worker environment."""
        if self.is_open:
            logger.info("Closing Antigravity connection...")
            self.is_open = False
