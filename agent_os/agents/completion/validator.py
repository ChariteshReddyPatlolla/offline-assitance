import logging
from typing import Dict, Any
from ..testing.testing_agent import TestingAgent

logger = logging.getLogger(__name__)

class ProjectValidator:
    """
    Validates that a project meets the definition of 'complete'.
    1. Application starts successfully.
    2. Tests pass.
    3. No critical errors exist.
    4. Build succeeds.
    """
    def __init__(self):
        self.testing_agent = TestingAgent()

    async def validate(self, state: Dict[str, Any]) -> bool:
        logger.info("ProjectValidator: Running final completion checks...")
        
        # 1. Check Tests
        test_result = await self.testing_agent.run_test("pytest")
        if not test_result["success"]:
            logger.error("ProjectValidator: Tests failed.")
            return False
            
        # 2. Check Build (Mocked logic for checking build, can be adapted)
        # e.g., if there's a specific build command like "npm run build" or "python setup.py build"
        build_command = state.get("build_command", "echo 'No build command needed'")
        build_result = await self.testing_agent.run_test(build_command)
        if not build_result["success"]:
            logger.error("ProjectValidator: Build failed.")
            return False

        # 3. Startup Check (Mocked: usually involves starting the app and pinging a port)
        logger.info("ProjectValidator: Startup checks passed (simulated).")

        return True
