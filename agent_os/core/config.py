import os
from pydantic import Field
from pydantic_settings import BaseSettings

class SystemConfig(BaseSettings):
    """
    Configuration for the Local Autonomous Agent OS.
    """
    
    # LLM Settings
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")
    DEFAULT_MODEL: str = Field(default="llama3")
    
    # Storage Settings
    CHROMA_DB_DIR: str = Field(default="./chroma_db")
    SQLITE_DB_PATH: str = Field(default="./agent_memory.db")
    
    # MCP Settings
    MCP_SERVERS_DIR: str = Field(default="./mcp_servers")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

config = SystemConfig()
