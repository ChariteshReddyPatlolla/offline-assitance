from pydantic import BaseModel, Field
from typing import List, Optional

class RequirementState(BaseModel):
    project_idea: str = Field(description="The core idea or goal the user wants to achieve.")
    identified_requirements: List[str] = Field(default_factory=list, description="List of clear, unambiguous requirements gathered so far.")
    missing_requirements: List[str] = Field(default_factory=list, description="Areas where information is missing or ambiguous.")
    is_clear: bool = Field(default=False, description="True if the requirements are sufficiently clear to proceed to planning.")

class RequirementSummary(BaseModel):
    summary: str = Field(description="A concise summary of the project requirements.")
    core_features: List[str] = Field(description="List of core features.")
    technical_constraints: List[str] = Field(default_factory=list, description="Any identified technical constraints (e.g. web, desktop, auth).")
