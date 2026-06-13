import uuid
from typing import List, Dict, Any
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .chroma_db import ChromaMemory

class RAGPipeline:
    """
    Handles ingestion, chunking, embedding, and saving to ChromaDB.
    """
    def __init__(self, vector_store: ChromaMemory):
        self.vector_store = vector_store
        # Optimized for code and text mixed
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )

    def ingest_text_file(self, file_path: str, source_metadata: Dict[str, Any]):
        """
        Loads a text file, chunks it, and ingests it into knowledge_documents.
        """
        loader = TextLoader(file_path, encoding='utf-8')
        docs = loader.load()
        chunks = self.text_splitter.split_documents(docs)
        
        documents = []
        metadatas = []
        ids = []
        
        for idx, chunk in enumerate(chunks):
            documents.append(chunk.page_content)
            
            # Merge source metadata with chunk specifics
            meta = source_metadata.copy()
            meta["source_file"] = file_path
            meta["chunk_index"] = idx
            metadatas.append(meta)
            
            ids.append(f"{file_path}_{uuid.uuid4().hex[:8]}")

        if documents:
            self.vector_store.add_memory(
                collection_name="knowledge_documents",
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            return len(documents)
        return 0

    def ingest_raw_text(self, text: str, source_metadata: Dict[str, Any]):
        """Chunks and ingests raw text string into semantic_memory."""
        chunks = self.text_splitter.split_text(text)
        
        documents = chunks
        metadatas = [source_metadata for _ in chunks]
        ids = [str(uuid.uuid4()) for _ in chunks]
        
        if documents:
            self.vector_store.add_memory(
                collection_name="semantic_memory",
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            return len(documents)
        return 0
