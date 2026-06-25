import sys
import os
import sqlite3
from typing import List, Dict, Any, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("sqlite")

DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "agent_memory.db").replace("\\", "/")

def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

@mcp.tool()
def read_query(query: str, db_path: Optional[str] = None) -> str:
    """
    Execute a SELECT SQL query on the database.
    Args:
        query: The SQL SELECT query string.
        db_path: Optional absolute database file path.
    """
    if not query.strip().lower().startswith("select") and not query.strip().lower().startswith("pragma"):
        return "❌ Error: Only SELECT or PRAGMA statements are allowed in read_query. Use write_query for mutations."
        
    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return "Query returned 0 rows."
            
        # Format as markdown table
        headers = list(rows[0].keys())
        header_row = "| " + " | ".join(headers) + " |"
        sep_row = "| " + " | ".join(["---"] * len(headers)) + " |"
        
        data_rows = []
        for r in rows:
            data_rows.append("| " + " | ".join(str(r[h]) for h in headers) + " |")
            
        return "\n".join([header_row, sep_row] + data_rows)
    except Exception as e:
        return f"❌ SQLite Error: {str(e)}"

@mcp.tool()
def write_query(query: str, db_path: Optional[str] = None) -> str:
    """
    Execute an INSERT, UPDATE, or DELETE SQL query on the database.
    Args:
        query: The SQL mutation query string.
        db_path: Optional absolute database file path.
    """
    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(query)
        conn.commit()
        changes = conn.total_changes
        conn.close()
        return f"✅ SQL Statement executed successfully. Total changes: {changes} rows modified."
    except Exception as e:
        return f"❌ SQLite Error: {str(e)}"

@mcp.tool()
def list_tables(db_path: Optional[str] = None) -> str:
    """
    List all tables available in the SQLite database.
    Args:
        db_path: Optional absolute database file path.
    """
    return read_query("SELECT name FROM sqlite_master WHERE type='table';", db_path)

@mcp.tool()
def describe_table(table_name: str, db_path: Optional[str] = None) -> str:
    """
    Get column structure, types, and constraints for a specific table.
    Args:
        table_name: Name of the table.
        db_path: Optional absolute database file path.
    """
    # SQL injection guard
    clean_name = "".join(c for c in table_name if c.isalnum() or c == "_")
    return read_query(f"PRAGMA table_info({clean_name});", db_path)

if __name__ == "__main__":
    mcp.run()
