import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class TestingAgent:
    """
    Executes an arbitrary test command or script locally via asyncio.create_subprocess_shell
    and captures stdout, stderr, and the return code.
    """
    async def run_test(self, command: str) -> Dict[str, Any]:
        logger.info(f"TestingAgent: Running command -> {command}")
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "success": process.returncode == 0,
                "exit_code": process.returncode,
                "stdout": stdout.decode("utf-8", errors="replace").strip(),
                "stderr": stderr.decode("utf-8", errors="replace").strip(),
                "command": command
            }
            
        except Exception as e:
            logger.error(f"TestingAgent Exception: {str(e)}")
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "command": command
            }
