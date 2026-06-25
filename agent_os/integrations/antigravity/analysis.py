from pydantic import BaseModel
from typing import Optional

class AnalysisResult(BaseModel):
    is_success: bool
    confidence: float
    feedback: str
    needs_reprompt: bool

class ResponseAnalyzer:
    """
    Parses Antigravity's output to find success, failure, or code states.
    """
    def analyze(self, raw_response: str) -> AnalysisResult:
        # Stub implementation for analyzing the raw response
        success_markers = ["completed successfully", "done", "success"]
        error_markers = ["error", "exception", "failed", "syntax"]
        
        raw_lower = raw_response.lower()
        
        is_error = any(marker in raw_lower for marker in error_markers)
        is_success = any(marker in raw_lower for marker in success_markers)
        
        if is_error:
            return AnalysisResult(is_success=False, confidence=0.9, feedback="Error detected in response.", needs_reprompt=True)
        elif is_success:
            return AnalysisResult(is_success=True, confidence=0.9, feedback="Task appears successful.", needs_reprompt=False)
        else:
            return AnalysisResult(is_success=False, confidence=0.5, feedback="Ambiguous response.", needs_reprompt=True)

class OutputValidator:
    """
    Validates the output quality against the original task requirements.
    """
    def validate(self, analysis: AnalysisResult, task_requirements: dict) -> bool:
        # Stub implementation
        # In a real system, this would cross-reference code changes or test results
        if not analysis.is_success:
            return False
            
        if analysis.confidence < 0.7:
            return False
            
        return True
