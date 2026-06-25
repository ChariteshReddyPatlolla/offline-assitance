import json
import logging
from typing import Dict, Any, Optional
from shared.database import SessionLocal
from shared.models import Session

logger = logging.getLogger(__name__)

class SessionManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SessionManager, cls).__new__(cls)
            cls._instance._cache = {}
            from agent_os.memory.chroma_db import ChromaMemory
            from agent_os.memory.workspace_indexer import WorkspaceIndexer
            cls._instance.indexer = WorkspaceIndexer(vector_store=ChromaMemory())
        return cls._instance

    def get_session_state(self, session_id: str) -> Dict[str, Any]:
        """Fetch the session state. Checks in-memory cache first, falls back to DB."""
        if session_id in self._cache:
            return self._cache[session_id]
            
        # Fallback to database
        db = SessionLocal()
        try:
            session = db.query(Session).filter(Session.id == session_id).first()
            if session:
                state = {
                    "current_app": session.current_app,
                    "current_project": session.current_project,
                    "current_directory": session.current_directory,
                    "current_file": session.current_file,
                    "current_terminal": session.current_terminal,
                    "current_browser_session": session.current_browser_session,
                    "current_browser_tab": session.current_browser_tab,
                    "current_workflow": session.current_workflow,
                    "open_tabs": json.loads(session.open_tabs) if session.open_tabs else [],
                    "last_action": session.last_action,
                    "previous_actions": json.loads(session.previous_actions) if session.previous_actions else [],
                }
                self._cache[session_id] = state
                return state
        except Exception as e:
            logger.error(f"Error fetching session state from DB: {e}")
        finally:
            db.close()
            
        # Return default state if not found
        default_state = {
            "current_app": None,
            "current_project": None,
            "current_directory": None,
            "current_file": None,
            "current_terminal": None,
            "current_browser_session": None,
            "current_browser_tab": None,
            "current_workflow": None,
            "open_tabs": [],
            "last_action": None,
            "previous_actions": [],
        }
        self._cache[session_id] = default_state
        return default_state

    def update_session_state(self, session_id: str, **kwargs) -> Dict[str, Any]:
        """Updates the session state in memory and persists to the database."""
        state = self.get_session_state(session_id)
        
        # Handle appending to previous_actions specifically if passed
        if "action" in kwargs:
            action = kwargs.pop("action")
            state["previous_actions"].append(action)
            # Keep only the last 50 actions to avoid bloat
            state["previous_actions"] = state["previous_actions"][-50:]
            state["last_action"] = action
            
        for key, value in kwargs.items():
            if key in state:
                state[key] = value
                if key == "current_project" and value:
                    self.indexer.start_indexing(value)
                
        self._cache[session_id] = state
        
        # Persist to database
        db = SessionLocal()
        try:
            session = db.query(Session).filter(Session.id == session_id).first()
            if session:
                for key, value in state.items():
                    if hasattr(session, key):
                        if isinstance(value, list) or isinstance(value, dict):
                            setattr(session, key, json.dumps(value))
                        else:
                            setattr(session, key, value)
                db.commit()
        except Exception as e:
            logger.error(f"Error updating session state in DB: {e}")
        finally:
            db.close()
            
        return state

    def clear_cache(self, session_id: Optional[str] = None):
        """Clears the cache for a specific session or all sessions."""
        if session_id:
            if session_id in self._cache:
                del self._cache[session_id]
        else:
            self._cache.clear()

session_manager = SessionManager()
