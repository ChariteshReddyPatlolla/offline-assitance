import json
from typing import Dict, Any
from .state import RequirementState

class RequirementValidator:
    def __init__(self, llm_provider):
        self.llm = llm_provider
        
    async def validate(self, conversation_history: str, current_idea: str) -> RequirementState:
        prompt = f"""
        Analyze this conversation about a project idea: "{current_idea}"
        History:
        {conversation_history}
        
        Determine the state of the requirements.
        Output your response strictly as a JSON object matching this schema:
        {{
            "project_idea": "The core idea",
            "identified_requirements": ["Req 1", "Req 2"],
            "missing_requirements": ["Missing 1", "Missing 2"],
            "is_clear": false
        }}
        """
        
        schema = RequirementState.model_json_schema()
        
        try:
            res = await self.llm.generate_structured(prompt=prompt, schema=schema, system_prompt="You are a Senior Architect analyzing requirements.")
            if res:
                return RequirementState(**res)
        except Exception:
            pass
            
        # Fallback to plain JSON parse if structured fails
        res = await self.llm.generate(prompt=prompt, system_prompt="Output ONLY valid JSON. You are a Senior Architect analyzing requirements.")
        try:
            if "```json" in res:
                res = res.split("```json")[1].split("```")[0].strip()
            elif "```" in res:
                res = res.split("```")[1].split("```")[0].strip()
            data = json.loads(res)
            return RequirementState(**data)
        except Exception as e:
            # Default fallback
            return RequirementState(project_idea=current_idea, missing_requirements=["Need more details to proceed."])
