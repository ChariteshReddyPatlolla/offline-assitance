import sqlite3
import json
from typing import Dict, List, Any, Optional

class SQLiteMemory:
    """
    Manages the relational storage for structured agent history using SQLite.
    Stores conversations, tasks, workflows, tool_executions, summaries, and user_preferences.
    """
    def __init__(self, db_path: str = "agent_memory.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Conversations Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Tasks Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    goal TEXT,
                    status TEXT,
                    plan_json TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Tool Executions Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tool_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    tool_name TEXT,
                    parameters TEXT,
                    result TEXT,
                    success BOOLEAN,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # User Preferences
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            conn.commit()

    def add_conversation(self, session_id: str, role: str, content: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content)
            )

    def get_recent_conversations(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM conversations WHERE session_id = ? ORDER BY timestamp DESC, id DESC LIMIT ?",
                (session_id, limit)
            )
            return [dict(row) for row in cursor.fetchall()][::-1]

    def save_task(self, task_id: str, goal: str, status: str, plan: Dict[str, Any]):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO tasks (task_id, goal, status, plan_json) VALUES (?, ?, ?, ?)",
                (task_id, goal, status, json.dumps(plan))
            )

    def log_tool_execution(self, task_id: str, tool_name: str, parameters: Dict[str, Any], result: str, success: bool):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO tool_executions (task_id, tool_name, parameters, result, success) VALUES (?, ?, ?, ?, ?)",
                (task_id, tool_name, json.dumps(parameters), result, success)
            )

    def set_preference(self, key: str, value: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO user_preferences (key, value) VALUES (?, ?)",
                (key, value)
            )

    def get_preference(self, key: str) -> Optional[str]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT value FROM user_preferences WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else None
