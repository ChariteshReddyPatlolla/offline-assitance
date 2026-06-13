from typing import Any, Dict

class PromptGenerator:
    """
    Translates execution DAG tasks into optimized prompts for Antigravity.
    """
    
    def generate_prompt(self, task: Dict[str, Any], context: Dict[str, Any] = None) -> str:
        """
        Generates a specific prompt to send to Antigravity based on the planned task.
        """
        task_id = task.get("task_id", "unknown_task")
        description = task.get("description", "Perform the assigned task.")
        
        prompt = f"""[AUTOMATED ORCHESTRATION PROMPT]
Task ID: {task_id}
Description: {description}

Please execute this task fully autonomously. Do not wait for user approval unless explicitly blocked.
"""
        
        if context and context.get("architecture"):
            prompt += f"\nContext:\nYou are working within this architecture constraints: {context.get('architecture').get('architecture', '')}"
            
        return prompt
