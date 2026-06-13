import logging
import asyncio
from typing import Dict, Any
from ..base_agent import BaseAgent
from ...interfaces.llm_provider import ILLMProvider
from ...memory.chroma_db import ChromaMemory
from .validator import ProjectValidator
from .doc_generator import DocumentGenerator
from .state_manager import ProjectStateManager

logger = logging.getLogger(__name__)

class ProjectCompletionAgent(BaseAgent):
    """
    Final node in the development lifecycle. Validates the project, generates docs,
    saves the state, and opens the project in VSCode.
    """
    def __init__(self, llm_provider: ILLMProvider, chroma: ChromaMemory):
        super().__init__(name="completion_agent", llm_provider=llm_provider)
        self.validator = ProjectValidator()
        self.doc_generator = DocumentGenerator(llm_provider)
        self.state_manager = ProjectStateManager(chroma)

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        messages = state.get("messages", [])
        content_log = "## Project Completion Agent Initiated\n\n"
        
        # Extract project name from architecture or fallback
        project_name = "unknown_project"
        arch = state.get("architecture", {})
        if isinstance(arch, dict) and "goal" in arch:
            project_name = arch["goal"][:50].replace(" ", "_")

        content_log += "1. **Validating Project...**\n"
        is_valid = await self.validator.validate(state)
        
        if not is_valid:
            content_log += "\u274c Validation failed! Project cannot be marked complete yet.\n"
            # Return back to orchestrator or end with failure
            return {
                "current_agent": self.get_name(),
                "next_node": "END",
                "messages": messages + [{"role": "assistant", "content": content_log}]
            }
        content_log += "\u2705 Validation passed (Application starts, tests pass, build succeeds).\n\n"
        
        content_log += "2. **Generating Documentation...**\n"
        await self.doc_generator.generate_all(state)
        content_log += "\u2705 README.md, ARCHITECTURE.md, SETUP.md, DEPLOYMENT.md, and CHANGELOG.md generated.\n\n"
        
        content_log += "3. **Saving Project State...**\n"
        self.state_manager.save_project_state(project_name, state)
        content_log += f"\u2705 Project `{project_name}` saved to persistent memory for future resumption.\n\n"
        
        content_log += "4. **Opening VSCode...**\n"
        try:
            # Execute "code ." command to open VSCode in the current workspace
            process = await asyncio.create_subprocess_shell("code .")
            await process.communicate()
            content_log += "\u2705 VSCode opened successfully.\n\n"
        except Exception as e:
            content_log += f"\u26a0\ufe0f Could not open VSCode automatically: {str(e)}\n\n"
            
        content_log += "### \ud83c\udf89 Project Complete!"

        return {
            "current_agent": self.get_name(),
            "next_node": "END",
            "messages": messages + [{"role": "assistant", "content": content_log}]
        }
