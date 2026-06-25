from pydantic import BaseModel
from typing import Any, Dict

class ValidationResult(BaseModel):
    is_valid: bool
    feedback: str

class ValidationEngine:
    """
    Validates the generated code or task output against the requirements.
    """
    def validate(self, raw_output: str, task: Dict[str, Any]) -> ValidationResult:
        """
        Checks if the task output is valid.
        """
        raw_lower = raw_output.lower()
        
        # Stub validation logic
        # In a real implementation, this would trigger unit tests, linters, or check specific completion markers
        error_keywords = ["syntaxerror", "exception", "traceback", "failed", "cannot complete"]
        success_keywords = ["task completed", "successfully", "done"]
        
        if any(err in raw_lower for err in error_keywords):
            return ValidationResult(
                is_valid=False, 
                feedback="Output contains error keywords. Please fix the exception or syntax error."
            )
            
        if any(suc in raw_lower for suc in success_keywords):
            return ValidationResult(
                is_valid=True, 
                feedback="Code successfully validated."
            )
            
        # Default fallback
        return ValidationResult(
            is_valid=True, 
            feedback="No errors detected. Assuming valid."
        )
