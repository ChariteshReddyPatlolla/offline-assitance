from langchain_core.tools import tool
from typing import Optional
from services.tools.approval_store import require_approval
from services.mcp.client import MCPClientManager

@tool
def read_query(query: str, db_path: Optional[str] = None) -> str:
    """
    Execute a SELECT SQL query on the database.
    Args:
        query: The SQL SELECT query string.
        db_path: Optional absolute database file path.
    """
    return MCPClientManager.get_instance().call_tool(
        "sqlite", "read_query", query=query, db_path=db_path
    )

@tool
def write_query(query: str, db_path: Optional[str] = None) -> str:
    """
    Execute an INSERT, UPDATE, or DELETE SQL query on the database. Requires explicit user approval.
    Args:
        query: The SQL mutation query string.
        db_path: Optional absolute database file path.
    """
    approval = require_approval(
        action_key=f"sqlite:{query[:200]}",
        description=f"Execute database write query:\n```sql\n{query}\n```",
        details={"query": query, "db_path": db_path, "dangerous": True}
    )
    if approval:
        return approval

    return MCPClientManager.get_instance().call_tool(
        "sqlite", "write_query", query=query, db_path=db_path
    )

@tool
def list_tables(db_path: Optional[str] = None) -> str:
    """
    List all tables available in the SQLite database.
    Args:
        db_path: Optional absolute database file path.
    """
    return MCPClientManager.get_instance().call_tool(
        "sqlite", "list_tables", db_path=db_path
    )

@tool
def describe_table(table_name: str, db_path: Optional[str] = None) -> str:
    """
    Get column structure, types, and constraints for a specific table.
    Args:
        table_name: Name of the table.
        db_path: Optional absolute database file path.
    """
    return MCPClientManager.get_instance().call_tool(
        "sqlite", "describe_table", table_name=table_name, db_path=db_path
    )
