import json
from typing import Any, Dict
from ..base_agent import BaseAgent
from ...interfaces.llm_provider import ILLMProvider
from .state import ProjectArchitecture

class ProjectArchitectAgent(BaseAgent):
    def __init__(self, llm_provider: ILLMProvider):
        super().__init__(name="architect", llm_provider=llm_provider)
        
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        requirements = state.get("requirements", {})
        messages = state.get("messages", [])
        if not requirements and messages:
            # Fallback if accessed directly without discovery
            requirements = {"project_idea": messages[-1].get("content", "No idea provided")}

        prompt = f"""
        Act as a Senior Software Architect. We have gathered the following validated requirements:
        
        Project Idea: {requirements.get('project_idea', '')}
        Identified Requirements: {requirements.get('identified_requirements', [])}
        Summary: {requirements.get('summary', {}).get('summary', '') if isinstance(requirements.get('summary'), dict) else requirements.get('summary', '')}
        
        Generate a comprehensive project architecture matching the provided schema exactly.
        """
        
        schema = ProjectArchitecture.model_json_schema()
        
        try:
            res = await self._llm_provider.generate_structured(prompt=prompt, schema=schema, system_prompt="You are a Senior Software Architect. Output valid JSON matching the schema.")
            if res:
                architecture_data = res
            else:
                raise ValueError("Structured generation returned empty")
        except Exception:
            # Fallback
            res = await self._llm_provider.generate(prompt=f"{prompt}\n\nOutput ONLY valid JSON matching this schema:\n{json.dumps(schema, indent=2)}", system_prompt="Output ONLY valid JSON.")
            try:
                if "```json" in res:
                    res = res.split("```json")[1].split("```")[0].strip()
                elif "```" in res:
                    res = res.split("```")[1].split("```")[0].strip()
                architecture_data = json.loads(res)
            except Exception:
                architecture_data = {"error": "Failed to parse architecture JSON."}

        # Save to memory index if available
        try:
            from services.session_manager import session_manager
            if hasattr(session_manager, 'indexer') and session_manager.indexer and hasattr(session_manager.indexer, 'vector_store'):
                session_manager.indexer.vector_store.add_memory(
                    collection_name="semantic_memory",
                    documents=[json.dumps(architecture_data, indent=2)],
                    metadatas=[{"type": "project_architecture", "source": "architect"}],
                    ids=["project_architecture_latest"]
                )
        except Exception as e:
            # Ignore memory write errors if indexer is not initialized
            pass

        content = "I have drafted the Project Architecture!\n\n"
        if isinstance(architecture_data, dict) and "architecture" in architecture_data:
            content += f"**Architecture**: {architecture_data.get('architecture')}\n"
            content += f"**Stack**: {', '.join(architecture_data.get('technology_stack', []))}\n"
            content += "\nThe full architectural specification (Milestones, APIs, Schema, Folder Structure) is now stored in memory and state."

        return {
            "current_agent": self.get_name(),
            "next_node": "END",
            "architecture": architecture_data,
            "messages": messages + [{"role": "assistant", "content": content}]
        }
