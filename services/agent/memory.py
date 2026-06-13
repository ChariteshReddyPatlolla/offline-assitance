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
