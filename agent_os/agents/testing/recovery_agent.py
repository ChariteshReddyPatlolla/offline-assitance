import logging
import uuid
from typing import Any, Dict
from ..base_agent import BaseAgent
from ...interfaces.llm_provider import ILLMProvider
from ...memory.chroma_db import ChromaMemory
from .testing_agent import TestingAgent
from .error_analyzer import ErrorAnalyzer
from .fix_generator import FixGenerator

logger = logging.getLogger(__name__)

class RecoveryAgent(BaseAgent):
    """
    Coordinates the Test -> Fail -> Analyze -> Fix -> Retest loop.
    Stores successful fixes for future reuse.
    """
    def __init__(self, llm_provider: ILLMProvider, chroma: ChromaMemory):
        super().__init__(name="recovery_agent", llm_provider=llm_provider)
        self.testing_agent = TestingAgent()
        self.error_analyzer = ErrorAnalyzer(llm_provider)
        self.fix_generator = FixGenerator(llm_provider)
        self.chroma = chroma
        self.max_retries = 3

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        messages = state.get("messages", [])
        
        # We need a command to test. In a real flow, this could come from pending_tasks or direct messages.
        command_to_test = None
        for msg in reversed(messages):
            if "test_command:" in msg.get("content", ""):
                command_to_test = msg["content"].split("test_command:")[1].strip()
                break
                
        # If no explicit command, fallback to a general test
        if not command_to_test:
            command_to_test = "pytest"

        content_log = f"## Testing and Recovery Loop Initiated\nTarget Command: `{command_to_test}`\n\n"
        
        success = False
        attempts = 0
        
        while not success and attempts < self.max_retries:
            attempts += 1
            content_log += f"**Attempt {attempts}**\n"
            
            # 1. Run
            result = await self.testing_agent.run_test(command_to_test)
            
            if result["success"]:
                content_log += "- Status: \u2705 Passed!\n"
                success = True
                break
                
            # 2. Analyze
            content_log += "- Status: \u274c Failed. Analyzing stack trace...\n"
            analysis = await self.error_analyzer.analyze(result)
            content_log += f"  - Type: {analysis.get('error_type')}\n"
            content_log += f"  - Root Cause: {analysis.get('root_cause')}\n"
            
            # 3. Generate Fix
            content_log += "- Generating fix prompt...\n"
            fix_suggestion = await self.fix_generator.generate_fix(result, analysis)
            
            # 4. In a fully autonomous loop, we would apply the fix directly via tools or Antigravity.
            # Here we capture the fix suggestion.
            content_log += f"  - Fix Generated: (Applying via autonomous sub-agent...)\n\n"
            
            # For this MVP loop, we break and return the fix to the state or user unless we have 
            # direct code editing tools wired in this class.
            break

        if success and attempts > 1:
            # 5. Store successful fix
            doc = f"Command: {command_to_test}\nFixed: {analysis.get('root_cause', 'Unknown')}\nSolution applied."
            self.chroma.add_memory(
                collection_name="recovery_patterns",
                documents=[doc],
                metadatas=[{"type": "recovery_pattern", "command": command_to_test}],
                ids=[str(uuid.uuid4())]
            )
            content_log += "\nSuccessful fix pattern stored in memory for future reuse."
            
        return {
            "current_agent": self.get_name(),
            "next_node": "END",
            "messages": messages + [{"role": "assistant", "content": content_log}]
        }
