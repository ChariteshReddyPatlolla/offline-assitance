from typing import Dict, Any
from ...interfaces.llm_provider import ILLMProvider

class FixGenerator:
    """
    Formulates a prompt for fixing the exact errors diagnosed by the ErrorAnalyzer.
    """
    def __init__(self, llm_provider: ILLMProvider):
        self.llm = llm_provider

    async def generate_fix(self, test_result: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """
        Generates a direct fix or code patch to resolve the failure.
        """
        prompt = f"""
        A script or test failed execution. 
        Command: {test_result.get('command')}
        
        Diagnostics:
        Error Type: {analysis.get('error_type')}
        Root Cause: {analysis.get('root_cause')}
        Location: {analysis.get('file_location')}
        
        STDERR snippet:
        {test_result.get('stderr')[-500:]}
        
        Please provide the exact code changes or terminal commands needed to fix this error. 
        Format your response as actionable instructions.
        """
        
        system_prompt = "You are a senior debugging specialist. Provide clear, actionable fixes."
        response = await self.llm.generate(prompt=prompt, system_prompt=system_prompt)
        return response
