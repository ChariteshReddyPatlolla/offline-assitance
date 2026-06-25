import os
import chromadb
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
import logging

logger = logging.getLogger(__name__)

# Initialize the embedding model
embeddings = OllamaEmbeddings(model="nomic-embed-text", keep_alive=-1)

# Path to the local vector database
PERSIST_DIRECTORY = os.path.join(os.getcwd(), "chroma_db")

# Initialize ChromaDB client and collection
client = chromadb.PersistentClient(path=PERSIST_DIRECTORY)

# Initialize LangChain Chroma wrapper
vector_store = Chroma(
    client=client,
    collection_name="omniagent_memory",
    embedding_function=embeddings,
)

def add_memory(text: str) -> bool:
    """Adds a fact or memory to the vector database."""
    try:
        vector_store.add_texts(texts=[text])
        logger.info(f"Added memory: {text}")
        return True
    except Exception as e:
        logger.error(f"Error adding memory: {e}")
        return False

def search_memory(query: str, k: int = 5) -> str:
    """Searches the vector database for relevant memories."""
    try:
        results = vector_store.similarity_search(query, k=k)
        if not results:
            return ""
        
        # Deduplicate results if necessary, or just return them
        memories = [doc.page_content for doc in results]
        return "\n".join(f"- {mem}" for mem in memories)
    except Exception as e:
        logger.error(f"Error searching memory: {e}")
        return ""

# Session context vector store
session_context_store = Chroma(
    client=client,
    collection_name="omniagent_session_context",
    embedding_function=embeddings,
)

def add_session_context(session_id: str, text: str) -> bool:
    """Adds an interaction or fast-path context to the session's vector store."""
    import time
    from shared.benchmark_logger import log_metric
    t_start = time.perf_counter()
    try:
        session_context_store.add_texts(texts=[text], metadatas=[{"session_id": session_id}])
        logger.info(f"Added session context: {text}")
        t_end = time.perf_counter()
        log_metric(session_id, "MemoryInsert", {"duration": t_end - t_start})
        return True
    except Exception as e:
        logger.error(f"Error adding session context: {e}")
        return False

def search_session_context(session_id: str, query: str, k: int = 3) -> str:
    """Searches the session vector store for relevant context."""
    try:
        results = session_context_store.similarity_search(query, k=k, filter={"session_id": session_id})
        if not results:
            return ""
        
        memories = [doc.page_content for doc in results]
        return "\n".join(f"- {mem}" for mem in memories)
    except Exception as e:
        logger.error(f"Error searching session context: {e}")
        return ""

# PDF Document RAG store
pdf_context_store = Chroma(
    client=client,
    collection_name="omniagent_pdf_rag",
    embedding_function=embeddings,
)

def add_pdf_context(document_id: str, texts: list[str]) -> bool:
    """Adds chunked text from a PDF into the vector database with the given document ID."""
    try:
        if not texts:
            return False
        metadatas = [{"document_id": document_id} for _ in texts]
        pdf_context_store.add_texts(texts=texts, metadatas=metadatas)
        logger.info(f"Added {len(texts)} chunks for document {document_id}")
        return True
    except Exception as e:
        logger.error(f"Error adding PDF context: {e}")
        return False

def search_pdf_context(document_id: str, query: str, k: int = 5) -> str:
    """Searches the PDF vector store for chunks matching the query and document_id."""
    try:
        results = pdf_context_store.similarity_search(query, k=k, filter={"document_id": document_id})
        if not results:
            return ""
        
        chunks = [doc.page_content for doc in results]
        return "\n---\n".join(chunks)
    except Exception as e:
        logger.error(f"Error searching PDF context: {e}")
        return ""
