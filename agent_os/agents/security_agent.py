import logging
import psutil
import os
import tempfile
import time
from typing import Any, Dict
from pydantic import Field
from agent_os.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class SecurityAgent(BaseAgent):
    """
    Agent responsible for deep security analysis.
    Checks for suspicious processes, open ports, and suspicious files.
    """
    
    agent_name: str = "SecurityAgent"
    system_prompt: str = (
        "You are OmniAgent's Security Expert. "
        "Your role is to deeply analyze the system for potential threats, backdoors, and suspicious activities. "
        "You can run network scans and process analysis to determine if there's any malware or unauthorized access. "
        "If you find anything suspicious, explain the threat level and provide recommendations to mitigate it. "
        "Keep your tone professional, authoritative, and direct."
    )
    
    def get_tools(self) -> list:
        return [
            {
                "type": "function",
                "function": {
                    "name": "analyze_open_ports",
                    "description": "Scans all listening network connections and identifies the processes holding them open.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "scan_temp_directory",
                    "description": "Scans the Windows temporary directory for recently created executables which may be malware droppers.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "hours_threshold": {
                                "type": "integer",
                                "description": "Number of hours to look back for modified files. Default is 24."
                            }
                        },
                        "required": []
                    }
                }
            }
        ]
        
    def execute_tool(self, tool_call: Dict[str, Any]) -> str:
        name = tool_call["function"]["name"]
        args = self.parse_arguments(tool_call)
        
        try:
            if name == "analyze_open_ports":
                return self._analyze_open_ports()
            elif name == "scan_temp_directory":
                return self._scan_temp_directory(args.get("hours_threshold", 24))
            else:
                return f"Unknown tool: {name}"
        except Exception as e:
            logger.error(f"Error in {name}: {e}")
            return f"Error executing {name}: {str(e)}"
            
    def _analyze_open_ports(self) -> str:
        results = []
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.status == 'LISTEN':
                    port = conn.laddr.port
                    try:
                        proc = psutil.Process(conn.pid)
                        name = proc.name()
                        exe = proc.exe()
                        results.append(f"Port: {port} | Process: {name} | Path: {exe}")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        results.append(f"Port: {port} | Process: Unknown (Access Denied)")
            
            if not results:
                return "No listening ports found."
            return "Listening Ports found:\n" + "\n".join(results)
        except Exception as e:
            return f"Failed to get network connections: {e}"

    def _scan_temp_directory(self, hours_threshold: int) -> str:
        temp_dir = tempfile.gettempdir()
        results = []
        now = time.time()
        threshold_seconds = hours_threshold * 3600
        
        try:
            for root, dirs, files in os.walk(temp_dir):
                if root != temp_dir and os.path.dirname(root) != temp_dir:
                    continue
                for f in files:
                    if f.lower().endswith(('.exe', '.bat', '.vbs', '.ps1')):
                        filepath = os.path.join(root, f)
                        try:
                            mtime = os.path.getmtime(filepath)
                            if now - mtime < threshold_seconds:
                                size = os.path.getsize(filepath)
                                results.append(f"File: {f} | Path: {filepath} | Size: {size} bytes")
                        except Exception:
                            pass
            
            if not results:
                return f"No suspicious executables modified in the last {hours_threshold} hours found in Temp."
            return f"Suspicious executables found in Temp (Last {hours_threshold} hours):\n" + "\n".join(results)
        except Exception as e:
            return f"Failed to scan temp directory: {e}"
