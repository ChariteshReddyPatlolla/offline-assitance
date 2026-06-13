from enum import Enum
from typing import Dict, Any

class RiskLevel(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class RiskClassifier:
    """
    Classifies the risk level of arbitrary tool calls and shell commands.
    """
    
    @staticmethod
    def evaluate(tool_name: str, parameters: Dict[str, Any]) -> RiskLevel:
        tool_name = tool_name.lower()
        cmd = parameters.get("command", "").lower()
        
        # 1. CRITICAL checks: credentials, emails, payments, system settings
        critical_tools = ["send_email", "process_payment", "update_credentials"]
        critical_keywords = ["sudo", "ssh", "aws", "passwd", "chmod", "chown", "stripe", "smtp", "mail"]
        if tool_name in critical_tools or any(keyword in cmd for keyword in critical_keywords):
            return RiskLevel.CRITICAL
            
        # 2. HIGH checks: delete files, terminate processes
        high_tools = ["delete_file", "rm", "kill_process", "kill"]
        high_keywords = ["rm ", "del ", "kill", "taskkill", "format"]
        if tool_name in high_tools or any(keyword in cmd for keyword in high_keywords):
            return RiskLevel.HIGH
            
        # 3. MEDIUM checks: install dependencies, modify project files
        medium_tools = ["write_file", "edit_file", "update_file", "git_commit"]
        medium_keywords = ["npm install", "pip install", "apt-get install", "git ", "apt install", "brew install"]
        if tool_name in medium_tools or any(keyword in cmd for keyword in medium_keywords):
            return RiskLevel.MEDIUM
            
        # 4. LOW checks: create files, write code, open apps, open websites, run tests
        low_tools = ["create_file", "read_file", "list_dir", "search", "read_url", "open_app", "run_test"]
        low_keywords = ["touch", "mkdir", "cat", "ls", "pytest", "npm test", "curl", "open", "start"]
        if tool_name in low_tools or any(keyword in cmd for keyword in low_keywords):
            return RiskLevel.LOW
            
        # Default safety fallback for unknown tool/command
        return RiskLevel.LOW if tool_name in low_tools else RiskLevel.MEDIUM
