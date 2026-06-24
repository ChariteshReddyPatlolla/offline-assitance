import redis
import json
import uuid
import sys

try:
    r = redis.Redis(host='localhost', port=6379, db=0)
    r.ping()
except Exception as e:
    print("Redis not running:", e)
    sys.exit(1)

task_id = str(uuid.uuid4())[:8]
task_payload = {
    "session_id": f"test_session_{task_id}",
    "file_path": "llm_thought_test.md",
    "messages": [
        {"type": "system", "data": {"content": "You are a helpful assistant."}},
        {"type": "human", "data": {"content": "Write a python script that just prints hello."}}
    ]
}

print("Pushing fixed task to llm_task_queue...")
r.rpush("llm_task_queue", json.dumps(task_payload))
print("Pushed!")
