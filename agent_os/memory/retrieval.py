from typing import List, Dict, Any, Optional
from .sqlite_db import SQLiteMemory
from .chroma_db import ChromaMemory

class HybridRetriever:
    """
    Combines dense semantic search (ChromaDB) with structured relational lookups (SQLite).
    Provides basic reranking and synthesized context gathering.
    """
    def __init__(self, sql_memory: SQLiteMemory, vector_memory: ChromaMemory):
        self.sql = sql_memory
        self.vector = vector_memory

    def gather_context(self, query: str, session_id: str, limit: int = 5) -> Dict[str, Any]:
        """
        Retrieves context from both semantic stores and structural stores.
        """
        # 1. Get recent chat history
        recent_chats = self.sql.get_recent_conversations(session_id, limit=5)
        
        # 2. Get semantic insights (Memories)
        semantic_results = self.vector.query_memory(
            collection_name="semantic_memory",
            query_texts=[query],
            n_results=limit
        )
        
        # 3. Get RAG Knowledge Docs
        knowledge_results = self.vector.query_memory(
            collection_name="knowledge_documents",
            query_texts=[query],
            n_results=limit
        )

        # 4. Reranking (Naïve concatenation for this iteration)
        # A true production system might use a Cross-Encoder here to score `query` vs `knowledge_results`
        
        return {
            "recent_history": recent_chats,
            "semantic_insights": semantic_results.get("documents", [[]])[0],
            "knowledge_docs": knowledge_results.get("documents", [[]])[0]
        }
