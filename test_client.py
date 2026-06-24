import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def run_test():
    import uuid
    session_id = str(uuid.uuid4())
    
    print("Testing /api/chat endpoint via TestClient...")
    for i in range(3):
        t0 = time.perf_counter()
        response = client.post("/api/chat/", json={
            "message": "Hello",
            "session_id": session_id if i > 0 else str(uuid.uuid4()),
            "user_id": "test_user_123"
        })
        t1 = time.perf_counter()
        
        if response.status_code == 200:
            print(f"Run {i+1} time: {t1 - t0:.3f}s | Response: {response.json()['content'][:50]}...")
        else:
            print(f"Run {i+1} failed: {response.status_code} - {response.text}")

if __name__ == "__main__":
    run_test()
