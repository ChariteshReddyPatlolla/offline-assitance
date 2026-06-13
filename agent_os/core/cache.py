import hashlib
import json
import sqlite3
from typing import Optional
from ..interfaces.llm_provider import ILLMProvider

class CachedLLMProvider(ILLMProvider):
    """
    A Decorator wrapping an existing ILLMProvider to add SQLite-backed caching.
    This saves immense compute and time during identical prompt requests (e.g. testing loops).
    """
    def __init__(self, base_provider: ILLMProvider, db_path: str = "llm_cache.db"):
        self.base_provider = base_provider
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS llm_cache (
                    prompt_hash TEXT PRIMARY KEY,
                    response TEXT
                )
            ''')

    def _hash_prompt(self, prompt: str, system_prompt: str) -> str:
        payload = f"{system_prompt}|||{prompt}"
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        h = self._hash_prompt(prompt, system_prompt)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT response FROM llm_cache WHERE prompt_hash = ?", (h,))
            row = cursor.fetchone()
            if row:
                return row[0]

        # Cache miss
        response = await self.base_provider.generate(prompt, system_prompt)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR REPLACE INTO llm_cache (prompt_hash, response) VALUES (?, ?)", (h, response))
            
        return response

    async def generate_structured(self, prompt: str, schema, system_prompt: str = "") -> Any:
        h = self._hash_prompt(prompt, system_prompt + str(schema))
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT response FROM llm_cache WHERE prompt_hash = ?", (h,))
            row = cursor.fetchone()
            if row:
                return schema.model_validate_json(row[0])

        response = await self.base_provider.generate_structured(prompt, schema, system_prompt)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR REPLACE INTO llm_cache (prompt_hash, response) VALUES (?, ?)", (h, response.model_dump_json()))
            
        return response

    async def stream(self, prompt: str, system_prompt: str = ""):
        # Streaming usually isn't cached cleanly due to generator yields. 
        # We will passthrough for now.
        async for chunk in self.base_provider.stream(prompt, system_prompt):
            yield chunk
