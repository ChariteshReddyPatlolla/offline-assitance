import json
from typing import Dict, Any
from ...interfaces.llm_provider import ILLMProvider

class ErrorAnalyzer:
    """
    Analyzes the stderr and stdout from the TestingAgent to extract
    structured root cause and classification using the LLM.
    """
    def __init__(self, llm_provider: ILLMProvider):
        self.llm = llm_provider

    async def analyze(self, test_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts stack trace info and returns structured JSON analysis.
        """
        prompt = f"""
        Analyze the following execution result and stack trace.
        
        Command: {test_result.get('command')}
        Exit Code: {test_result.get('exit_code')}
        
        STDOUT:
        {test_result.get('stdout')[-1000:]} # Truncating to last 1000 chars
        
        STDERR:
        {test_result.get('stderr')}
        
        Output valid JSON with the following keys:
        - "root_cause": Detailed description of why it failed.
        - "error_type": A classification (e.g., SyntaxError, AssertionError, ModuleNotFoundError).
        - "file_location": The specific file and line number if found in the stack trace, or "Unknown".
        """
        
        system_prompt = "You are an expert systems diagnostics engine. Always output pure JSON."
        
        try:
            response = await self.llm.generate(prompt=prompt, system_prompt=system_prompt)
            if "{" in response and "}" in response:
                json_str = response[response.find("{"):response.rfind("}")+1]
                return json.loads(json_str)
            return {"root_cause": "Failed to parse analysis.", "error_type": "Unknown", "file_location": "Unknown"}
        except Exception as e:
            return {
                "root_cause": f"Analysis exception: {str(e)}", 
                "error_type": "AnalyzerException", 
                "file_location": "Unknown"
            }
