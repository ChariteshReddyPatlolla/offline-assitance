import pytest
import asyncio
import os
import shutil
from agent_os.core.recovery import FailureAnalyzer, RecoveryEngine
from agent_os.core.models import PlannedTask
from agent_os.interfaces.llm_provider import ILLMProvider
from agent_os.memory.chroma_db import ChromaMemory

class MockDiagnosticsLLM(ILLMProvider):
    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        if "Analyze" in prompt:
            return '{"root_cause": "Typo in command", "error_type": "SyntaxError", "confidence_score": 90.0}'
        else:
            return "Fix: use 'git clone' instead of 'git clne'"
    async def generate_structured(self, prompt, schema, system_prompt=""): return None
    async def stream(self, prompt, system_prompt=""): return None

@pytest.fixture
def chroma_mem():
    db_dir = "./test_chroma_recovery"
    try:
        if os.path.exists(db_dir):
            shutil.rmtree(db_dir, ignore_errors=True)
    except OSError:
        pass
    mem = ChromaMemory(db_dir=db_dir)
    yield mem
    try:
        if os.path.exists(db_dir):
            del mem
            shutil.rmtree(db_dir, ignore_errors=True)
    except OSError:
        pass

@pytest.mark.asyncio
async def test_failure_analyzer():
    analyzer = FailureAnalyzer(MockDiagnosticsLLM())
    result = await analyzer.analyze("git clne is not a command")
    assert result["error_type"] == "SyntaxError"
    assert result["confidence_score"] == 90.0

@pytest.mark.asyncio
async def test_recovery_engine(chroma_mem):
    engine = RecoveryEngine(MockDiagnosticsLLM(), chroma_mem)
    
    # Store a fake recovery
    engine.store_successful_recovery("git clne", "git clone")
    
    # Draft recovery
    task = PlannedTask(task_id="t1", description="Clone repo")
    plan = await engine.draft_recovery_plan(task, {"root_cause": "Typo in command", "error_type": "SyntaxError"})
    assert "git clone" in plan
