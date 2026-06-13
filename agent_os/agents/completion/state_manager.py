import uuid
import json
import logging
from typing import Dict, Any
from ...memory.chroma_db import ChromaMemory

logger = logging.getLogger(__name__)

class ProjectStateManager:
    """
    Serializes and stores the final AgentState into ChromaDB for future resumption.
    """
    def __init__(self, chroma: ChromaMemory):
        self.chroma = chroma

    def save_project_state(self, project_name: str, state: Dict[str, Any]):
        """
        Stores the current project state (architecture, execution results) in memory.
        """
        logger.info(f"Saving project state for: {project_name}")
        
        # We selectively serialize parts of the state to avoid large payloads.
        persisted_data = {
            "project_name": project_name,
            "architecture": state.get("architecture", {}),
            "execution_plan": state.get("execution_plan", {}),
            "completed_tasks": list(state.get("execution_results", {}).keys())
        }
        
        document_text = f"Project State for: {project_name}\nData: {json.dumps(persisted_data)}"
        
        self.chroma.add_memory(
            collection_name="saved_projects",
            documents=[document_text],
            metadatas=[{
                "type": "project_snapshot", 
                "project_name": project_name,
                "state_json": json.dumps(persisted_data)
            }],
            ids=[str(uuid.uuid4())]
        )
        logger.info("Project state saved successfully.")
