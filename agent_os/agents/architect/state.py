from pydantic import BaseModel, Field
from typing import List, Dict, Any

class FunctionalRequirement(BaseModel):
    id: str
    description: str

class NonFunctionalRequirement(BaseModel):
    id: str
    category: str
    description: str

class UserStory(BaseModel):
    id: str
    actor: str
    action: str
    benefit: str

class DatabaseSchema(BaseModel):
    tables: List[Dict[str, Any]] = Field(description="List of table definitions including columns and relationships.")

class APIDefinition(BaseModel):
    endpoints: List[Dict[str, Any]] = Field(description="List of API endpoints including method, path, and payload description.")

class Milestone(BaseModel):
    name: str
    description: str
    deliverables: List[str]

class ProjectArchitecture(BaseModel):
    functional_requirements: List[FunctionalRequirement]
    non_functional_requirements: List[NonFunctionalRequirement]
    user_stories: List[UserStory]
    architecture: str = Field(description="High-level architecture pattern (e.g. Microservices, Monolithic, Serverless).")
    database_schema: DatabaseSchema
    apis: APIDefinition
    folder_structure: List[str] = Field(description="Suggested high-level folder structure.")
    technology_stack: List[str] = Field(description="List of technologies (e.g. React, FastAPI, PostgreSQL).")
    milestones: List[Milestone]
