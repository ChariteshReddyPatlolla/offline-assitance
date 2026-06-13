from typing import List

class QuestionGenerator:
    def __init__(self, llm_provider):
        self.llm = llm_provider
        
    async def generate_questions(self, idea: str, missing: List[str]) -> str:
        prompt = f"""
        We are building: {idea}
        We need clarity on: {missing}
        
        Generate exactly 1 to 3 concise follow-up questions to ask the user.
        Format them as bullet points. Do not include introductory text.
        """
        response = await self.llm.generate(prompt=prompt, system_prompt="You are a Senior Software Architect gathering requirements.")
        return response.strip()
