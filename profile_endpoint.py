import os
import sys
import time
import asyncio
from shared.database import SessionLocal
from shared import schemas
from api.routes.chat import chat_endpoint

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

async def run():
    db = SessionLocal()
    req = schemas.ChatRequest(
        session_id="test-session-123",
        user_id="test-user",
        message="Hello"
    )
    
    print("Starting chat_endpoint profiling...")
    t0 = time.perf_counter()
    res = await chat_endpoint(req, db)
    t1 = time.perf_counter()
    print(f"Total chat_endpoint time: {t1 - t0:.2f}s")

if __name__ == "__main__":
    asyncio.run(run())
