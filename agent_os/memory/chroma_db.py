import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional

class ChromaMemory:
    """
    Manages semantic vector storage using ChromaDB for dense embeddings.
    Stores semantic memory insights and RAG knowledge documents.
    """
    def __init__(self, db_dir: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(path=db_dir, settings=Settings(anonymized_telemetry=False))
        
        from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
        
        # Use Ollama for embeddings to ensure it runs on the GPU!
        self.embedding_fn = OllamaEmbeddingFunction(
            model_name="nomic-embed-text",
            url="http://localhost:11434/api/embeddings"
        )
        
        # Collections
        self.semantic_memory = self.client.get_or_create_collection(
            name="semantic_memory",
            metadata={"description": "Stores generalized knowledge and project insights."},
            embedding_function=self.embedding_fn
        )
        self.knowledge_docs = self.client.get_or_create_collection(
            name="knowledge_documents",
            metadata={"description": "Stores RAG chunks from ingested files."},
            embedding_function=self.embedding_fn
        )
        self.recovery_patterns = self.client.get_or_create_collection(
            name="recovery_patterns",
            metadata={"description": "Stores historical stack traces and their successful fixes."},
            embedding_function=self.embedding_fn
        )

    def add_memory(self, collection_name: str, documents: List[str], metadatas: List[Dict[str, Any]], ids: List[str]):
        """Adds vectorized knowledge (assumes default chroma embedding or explicit vectors if provided)."""
        collection = self.client.get_collection(collection_name)
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def query_memory(self, collection_name: str, query_texts: List[str], n_results: int = 5, where: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Queries the vector database based on dense similarity and optional metadata filters."""
        collection = self.client.get_collection(collection_name)
        return collection.query(
            query_texts=query_texts,
            n_results=n_results,
            where=where
        )

    def delete_memory(self, collection_name: str, ids: List[str]):
        """Deletes memories by ID."""
        collection = self.client.get_collection(collection_name)
        collection.delete(ids=ids)
