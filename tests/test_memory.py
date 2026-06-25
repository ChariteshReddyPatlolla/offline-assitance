import pytest
import os
import shutil
from agent_os.memory.sqlite_db import SQLiteMemory
from agent_os.memory.chroma_db import ChromaMemory
from agent_os.memory.rag_pipeline import RAGPipeline
from agent_os.memory.retrieval import HybridRetriever

@pytest.fixture
def sqlite_memory():
    db_path = "test_memory.db"
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except OSError:
        pass
    mem = SQLiteMemory(db_path=db_path)
    yield mem
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except OSError:
        pass

@pytest.fixture
def chroma_memory():
    db_dir = "./test_chroma"
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

def test_sqlite_conversations(sqlite_memory):
    sqlite_memory.add_conversation("session_1", "user", "Hello")
    sqlite_memory.add_conversation("session_1", "assistant", "Hi there")
    
    recent = sqlite_memory.get_recent_conversations("session_1", 5)
    assert len(recent) == 2
    assert recent[0]["role"] == "user"
    assert recent[1]["role"] == "assistant"

def test_sqlite_preferences(sqlite_memory):
    sqlite_memory.set_preference("theme", "dark")
    assert sqlite_memory.get_preference("theme") == "dark"
    sqlite_memory.set_preference("theme", "light")
    assert sqlite_memory.get_preference("theme") == "light"
    assert sqlite_memory.get_preference("unknown") is None

def test_rag_pipeline(chroma_memory):
    pipeline = RAGPipeline(chroma_memory)
    
    # Ingest raw text
    count = pipeline.ingest_raw_text("The agent architecture uses LangGraph.", source_metadata={"doc": "test"})
    assert count > 0
    
    # Query Chroma
    results = chroma_memory.query_memory("semantic_memory", ["architecture"])
    assert len(results["documents"][0]) > 0
    assert "LangGraph" in results["documents"][0][0]

def test_hybrid_retriever(sqlite_memory, chroma_memory):
    pipeline = RAGPipeline(chroma_memory)
    pipeline.ingest_raw_text("The sky is blue.", source_metadata={"source": "test"})
    
    sqlite_memory.add_conversation("s1", "user", "Chat log here.")
    
    retriever = HybridRetriever(sqlite_memory, chroma_memory)
    context = retriever.gather_context("sky", "s1", limit=1)
    
    assert len(context["recent_history"]) == 1
    assert "sky" in context["semantic_insights"][0]
