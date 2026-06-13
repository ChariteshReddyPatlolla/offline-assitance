from typing import Any, Dict
from ..base_agent import BaseAgent
from ...interfaces.llm_provider import ILLMProvider
from .validator import RequirementValidator
from .question_generator import QuestionGenerator
from .state import RequirementSummary
import json

class RequirementDiscoveryAgent(BaseAgent):
    """
    Acts as a Senior Architect to discover and clarify project requirements.
    """
    def __init__(self, llm_provider: ILLMProvider):
        super().__init__(name="discovery", llm_provider=llm_provider)
        self.validator = RequirementValidator(llm_provider)
        self.generator = QuestionGenerator(llm_provider)
        
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        messages = state.get("messages", [])
        if not messages:
            return {"next_node": "END", "current_agent": self.get_name()}
            
        # Build history string
        history = "\n".join([f"{m['role']}: {m.get('content', '')}" for m in messages[-5:]])
        
        # Get existing requirements state if any
        req_state_dict = state.get("requirements", {})
        current_idea = req_state_dict.get("project_idea", messages[0].get("content", ""))
        
        # Validate current understanding
        validation_result = await self.validator.validate(history, current_idea)
        
        if validation_result.is_clear:
            # Requirements are clear. Generate summary.
            prompt = f"Summarize these requirements:\nIdea: {validation_result.project_idea}\nReqs: {validation_result.identified_requirements}"
            schema = RequirementSummary.model_json_schema()
            
            try:
                summary_data = await self._llm_provider.generate_structured(prompt=prompt, schema=schema, system_prompt="Summarize requirements.")
            except Exception:
                # Fallback
                summary_data = {
                    "summary": validation_result.project_idea, 
                    "core_features": validation_result.identified_requirements,
                    "technical_constraints": []
                }
                
            # Update state
            new_reqs = validation_result.model_dump()
            new_reqs["summary"] = summary_data
            
            # Send completion message
            content = "Requirements are clear! Handing off to the Architect.\n\n"
            if isinstance(summary_data, dict):
                content += f"**Summary**: {summary_data.get('summary', '')}\n"
                for f in summary_data.get('core_features', []):
                    content += f"- {f}\n"
            else:
                content += str(summary_data)
            
            return {
                "current_agent": self.get_name(),
                "next_node": "architect",
                "requirements": new_reqs,
                "messages": messages + [{"role": "assistant", "content": content}]
            }
        else:
            # Ambiguity detected. Ask questions.
            questions = await self.generator.generate_questions(
                validation_result.project_idea, 
                validation_result.missing_requirements
            )
            
            return {
                "current_agent": self.get_name(),
                "next_node": "END", # Return to user
                "requirements": validation_result.model_dump(),
                "messages": messages + [{"role": "assistant", "content": questions}]
            }
