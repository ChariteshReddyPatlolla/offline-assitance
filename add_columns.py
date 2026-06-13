import sqlite3

def add_column(cursor, table, column, dtype):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {dtype}")
        print(f"Added {column} to {table}")
    except sqlite3.OperationalError as e:
        print(f"Error adding {column} to {table}: {e}")

conn = sqlite3.connect('omniagent.db')
c = conn.cursor()

# Update messages table to support tool calls and outputs
add_column(c, 'messages', 'tool_calls', 'TEXT') # JSON string of tool calls
add_column(c, 'messages', 'tool_call_id', 'VARCHAR') # ID for ToolMessage matching
add_column(c, 'messages', 'name', 'VARCHAR') # tool name for ToolMessage

conn.commit()
conn.close()
