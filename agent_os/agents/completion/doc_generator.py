import os
import logging
from typing import Dict, Any
from ...interfaces.llm_provider import ILLMProvider

logger = logging.getLogger(__name__)

class DocumentGenerator:
    """
    Synthesizes project state and generates required documentation files.
    """
    def __init__(self, llm_provider: ILLMProvider):
        self.llm = llm_provider
        self.docs_to_generate = [
            ("README.md", "A comprehensive overview of the project, features, and quickstart."),
            ("ARCHITECTURE.md", "Detailed technical architecture, components, and design decisions."),
            ("SETUP.md", "Step-by-step instructions for local development setup and prerequisites."),
            ("DEPLOYMENT.md", "Instructions for deploying the application to production."),
            ("CHANGELOG.md", "Initial changelog detailing the v1.0.0 release features.")
        ]

    async def generate_all(self, state: Dict[str, Any], output_dir: str = "."):
        """
        Generates and writes all required documentation.
        """
        architecture = state.get("architecture", {})
        execution_plan = state.get("execution_plan", {})
        
        context = f"Architecture Context:\n{architecture}\n\nExecution DAG:\n{execution_plan}"

        for filename, description in self.docs_to_generate:
            prompt = f"""
            Based on the following project context, generate the `{filename}` file.
            Purpose: {description}
            
            Context:
            {context}
            
            Output ONLY the raw markdown content for the file. Do not wrap in markdown code blocks if the entire response is the file.
            """
            
            logger.info(f"Generating {filename}...")
            content = await self.llm.generate(prompt=prompt, system_prompt="You are a senior technical writer.")
            
            # Clean up markdown code blocks if present
            if content.startswith("```markdown"):
                content = content[11:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
                
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content.strip())
                
            logger.info(f"Successfully wrote {filename}")
