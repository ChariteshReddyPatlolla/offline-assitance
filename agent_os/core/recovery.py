from typing import Dict, Any, List, Optional
import json
import uuid
from ..interfaces.llm_provider import ILLMProvider
from ..memory.chroma_db import ChromaMemory
from ..core.models import PlannedTask

class FailureAnalyzer:
    """
    Parses stack traces and error messages to classify the failure
    and output a standardized root cause.
    """
    def __init__(self, llm_provider: ILLMProvider):
        self.llm = llm_provider

    async def analyze(self, error_message: str, context: str = "") -> Dict[str, Any]:
        prompt = f"""
        Analyze the following failure.
        Context: {context}
        Error: {error_message}
        
        Output valid JSON with the following keys:
        - "root_cause": Brief description of why it failed.
        - "error_type": A classification (e.g., SyntaxError, NetworkTimeout, PermissionDenied).
        - "confidence_score": 1-100 float representing your confidence in this diagnosis.
        """
        system_prompt = "You are an expert systems diagnostics engine. Always output pure JSON."
        
        # We assume ILLMProvider has a json/structured generation mode or we just parse the string.
        # For this skeleton, we will mock the JSON parsing behavior using the standard generate.
        try:
            response = await self.llm.generate(prompt=prompt, system_prompt=system_prompt)
            # Find json block (naive extraction for skeleton)
            if "{" in response and "}" in response:
                json_str = response[response.find("{"):response.rfind("}")+1]
                return json.loads(json_str)
            return {"root_cause": "Unknown", "error_type": "Unknown", "confidence_score": 0.0}
        except Exception as e:
            return {
                "root_cause": f"Analysis failed: {str(e)}", 
                "error_type": "AnalysisError", 
                "confidence_score": 0.0
            }


class RecoveryEngine:
    """
    Queries ChromaDB for historically successful fixes, and constructs 
    a recovery plan for the current failure.
    """
    def __init__(self, llm_provider: ILLMProvider, chroma: ChromaMemory):
        self.llm = llm_provider
        self.chroma = chroma

    async def draft_recovery_plan(self, task: PlannedTask, analysis: Dict[str, Any]) -> str:
        """
        Uses semantic search to find previous fixes for similar errors,
        then uses the LLM to draft a recovery patch.
        """
        # 1. Query past recovery patterns
        query_text = f"{analysis.get('error_type', '')}: {analysis.get('root_cause', '')}"
        
        results = self.chroma.query_memory(
            collection_name="recovery_patterns",
            query_texts=[query_text],
            n_results=3
        )
        
        historical_context = ""
        if results and results.get("documents"):
            historical_context = "\n".join(results["documents"][0])
            
        prompt = f"""
        Draft a step-by-step recovery plan or code patch to fix this failure.
        Task Goal: {task.description}
        Root Cause: {analysis.get('root_cause')}
        Error Type: {analysis.get('error_type')}
        
        Historically successful similar fixes:
        {historical_context}
        
        Provide the explicit recovery instructions.
        """
        
        recovery_plan = await self.llm.generate(prompt=prompt, system_prompt="You are a recovery engineering expert.")
        return recovery_plan

    def store_successful_recovery(self, error_message: str, applied_fix: str):
        """
        Once a task succeeds after failing, this is called to embed the 
        lesson into ChromaDB.
        """
        document = f"Error: {error_message}\nFix Applied: {applied_fix}"
        self.chroma.add_memory(
            collection_name="recovery_patterns",
            documents=[document],
            metadatas=[{"type": "recovery_pattern"}],
            ids=[str(uuid.uuid4())]
        )
