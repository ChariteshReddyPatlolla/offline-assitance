import os
import ast
import threading
from typing import List, Dict, Any, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from agent_os.memory.chroma_db import ChromaMemory
import logging

logger = logging.getLogger(__name__)

# Extensions to index
SUPPORTED_EXTENSIONS = {".py", ".js", ".ts", ".md", ".json", ".txt"}
EXCLUDE_DIRS = {".git", "node_modules", "venv", "__pycache__", ".venv"}

class ProjectEventHandler(FileSystemEventHandler):
    def __init__(self, indexer):
        self.indexer = indexer

    def on_modified(self, event):
        if not event.is_directory and self._is_supported(event.src_path):
            self.indexer.index_file(event.src_path)

    def on_created(self, event):
        if not event.is_directory and self._is_supported(event.src_path):
            self.indexer.index_file(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory and self._is_supported(event.src_path):
            self.indexer.remove_file(event.src_path)

    def _is_supported(self, path: str) -> bool:
        return any(path.endswith(ext) for ext in SUPPORTED_EXTENSIONS)

class WorkspaceIndexer:
    """
    Background service that indexes a project directory, builds an AST/knowledge graph
    for supported files, and manages a live watchdog observer.
    """
    def __init__(self, vector_store: ChromaMemory):
        self.vector_store = vector_store
        self.observer = None
        self.current_project = None
        
        # Ensure collection exists
        self.collection_name = "project_rag"
        self.vector_store.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Stores RAG chunks and AST graphs from workspace files."}
        )

    def start_indexing(self, project_path: str):
        if self.current_project == project_path:
            return # Already indexing this project
            
        self.stop() # Stop any existing observer
        
        self.current_project = project_path
        
        # 1. Full directory index in background
        threading.Thread(target=self._initial_index, args=(project_path,), daemon=True).start()
        
        # 2. Start File Watcher
        self.observer = Observer()
        event_handler = ProjectEventHandler(self)
        self.observer.schedule(event_handler, project_path, recursive=True)
        self.observer.start()

    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            self.current_project = None

    def _initial_index(self, project_path: str):
        logger.info(f"Starting workspace indexing for {project_path}")
        for root, dirs, files in os.walk(project_path):
            # Prune excluded directories in-place
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            for file in files:
                if any(file.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                    filepath = os.path.join(root, file)
                    self.index_file(filepath)
        logger.info("Workspace indexing complete.")

    def index_file(self, filepath: str):
        try:
            # First remove existing chunks for this file
            self.remove_file(filepath)
            
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            documents = []
            metadatas = []
            ids = []
            
            # Basic file chunk
            documents.append(content[:4000]) # Top 4000 chars as file summary
            metadatas.append({"filepath": filepath, "type": "file_content"})
            ids.append(f"{filepath}::file")
            
            # Python AST parsing for granular symbols/functions/classes
            if filepath.endswith('.py'):
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            class_code = ast.get_source_segment(content, node) or f"class {node.name}"
                            documents.append(class_code)
                            metadatas.append({"filepath": filepath, "type": "class", "name": node.name})
                            ids.append(f"{filepath}::class::{node.name}")
                        elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                            func_code = ast.get_source_segment(content, node) or f"def {node.name}"
                            documents.append(func_code)
                            metadatas.append({"filepath": filepath, "type": "function", "name": node.name})
                            ids.append(f"{filepath}::function::{node.name}")
                except Exception as ast_e:
                    logger.debug(f"AST parse error in {filepath}: {ast_e}")
                    
            if documents:
                self.vector_store.add_memory(
                    collection_name=self.collection_name,
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
        except Exception as e:
            logger.error(f"Error indexing {filepath}: {e}")

    def remove_file(self, filepath: str):
        try:
            collection = self.vector_store.client.get_collection(self.collection_name)
            # Find all ids for this filepath
            res = collection.get(where={"filepath": filepath})
            if res and res["ids"]:
                self.vector_store.delete_memory(self.collection_name, ids=res["ids"])
        except Exception:
            pass # Collection might not exist or be empty
