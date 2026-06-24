import os
import sys
import json
import time
import asyncio
import subprocess
import threading
from typing import Any, Dict

# Ensure psutil is installed
try:
    import psutil
except ImportError:
    print("Installing psutil...")
    subprocess.run([sys.executable, "-m", "pip", "install", "psutil", "typing_extensions"], check=True)
    import psutil

# Ensure we're running from the right directory
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from shared.database import SessionLocal
from shared import schemas
from api.routes.chat import chat_endpoint

# --- Profiling Data Structures ---
results = []
current_metrics = {
    "llm_calls": 0,
    "llm_time": 0.0,
    "intent_time": 0.0,
    "memory_time": 0.0,
    "prompt_chars": 0,
    "output_chars": 0,
    "tools_called": []
}

resource_metrics = {
    "cpu": [],
    "ram": [],
}

stop_monitoring = False

def resource_monitor():
    while not stop_monitoring:
        resource_metrics["cpu"].append(psutil.cpu_percent(interval=0.1))
        resource_metrics["ram"].append(psutil.virtual_memory().percent)
        time.sleep(0.5)

# --- Monkey Patches ---
import langchain_ollama
original_chat_ollama_invoke = langchain_ollama.ChatOllama.invoke

def patched_invoke(self, input_messages, *args, **kwargs):
    global current_metrics
    start = time.perf_counter()
    res = original_chat_ollama_invoke(self, input_messages, *args, **kwargs)
    elapsed = time.perf_counter() - start
    
    current_metrics["llm_calls"] += 1
    current_metrics["llm_time"] += elapsed
    current_metrics["prompt_chars"] += sum(len(m.content) for m in input_messages if isinstance(m.content, str))
    if getattr(res, "content", None):
        current_metrics["output_chars"] += len(res.content)
    return res

langchain_ollama.ChatOllama.invoke = patched_invoke

import services.fast_path
original_process_fast_path = services.fast_path.process_fast_path_commands

def patched_fast_path(clauses):
    global current_metrics
    start = time.perf_counter()
    res = original_process_fast_path(clauses)
    current_metrics["intent_time"] += time.perf_counter() - start
    return res

services.fast_path.process_fast_path_commands = patched_fast_path

# Monkey patch memory search to profile
import services.agent.memory
if hasattr(services.agent.memory, "search_memory"):
    original_search_memory = services.agent.memory.search_memory
    def patched_search_memory(query, k=5):
        global current_metrics
        start = time.perf_counter()
        res = original_search_memory(query, k)
        current_metrics["memory_time"] += time.perf_counter() - start
        return res
    services.agent.memory.search_memory = patched_search_memory


# --- Test Suite ---
test_prompts = [
    "Hi",
    "Hello",
    "Hey",
    "Thanks",
    "What is your name?",
    "What is 2+2?",
    "Tell me a joke",
    "Good morning",
    "Good evening",
    "Are you there?",
]

async def run_benchmark():
    global current_metrics, stop_monitoring
    
    print("Starting Resource Monitor...")
    monitor_thread = threading.Thread(target=resource_monitor, daemon=True)
    monitor_thread.start()

    db = SessionLocal()
    import uuid
    test_user_id = str(uuid.uuid4())
    
    for i, prompt in enumerate(test_prompts):
        print(f"\n--- Test {i+1}: '{prompt}' ---")
        
        # Reset metrics
        current_metrics = {
            "llm_calls": 0,
            "llm_time": 0.0,
            "intent_time": 0.0,
            "memory_time": 0.0,
            "prompt_chars": 0,
            "output_chars": 0,
            "tools_called": []
        }
        
        # We use a new session ID for some tests to simulate fresh context
        session_id = str(uuid.uuid4()) if i % 2 == 0 else test_user_id
        
        req = schemas.ChatRequest(
            session_id=session_id,
            user_id=test_user_id,
            message=prompt
        )
        
        t0 = time.perf_counter()
        try:
            response = await chat_endpoint(req, db)
            final_text = getattr(response, "content", getattr(response, "message", str(response)))
        except Exception as e:
            print(f"Error during test: {e}")
            final_text = f"Error: {e}"
            
        t1 = time.perf_counter()
        
        total_time = t1 - t0
        print(f"Total Time: {total_time:.2f}s | LLM Time: {current_metrics['llm_time']:.2f}s | Intent: {current_metrics['intent_time']:.4f}s")
        
        results.append({
            "prompt": prompt,
            "total_time": total_time,
            "llm_calls": current_metrics["llm_calls"],
            "llm_time": current_metrics["llm_time"],
            "intent_time": current_metrics["intent_time"],
            "memory_time": current_metrics["memory_time"],
            "prompt_tokens_est": current_metrics["prompt_chars"] // 4,
            "output_tokens_est": current_metrics["output_chars"] // 4,
            "response": final_text
        })
        
        # Small delay between requests to let system breathe
        await asyncio.sleep(1)
        
    db.close()
    
    stop_monitoring = True
    monitor_thread.join(timeout=2)
    
    avg_cpu = sum(resource_metrics["cpu"]) / len(resource_metrics["cpu"]) if resource_metrics["cpu"] else 0
    max_ram = max(resource_metrics["ram"]) if resource_metrics["ram"] else 0
    
    final_output = {
        "results": results,
        "resources": {
            "avg_cpu_percent": avg_cpu,
            "max_ram_percent": max_ram
        }
    }
    
    with open("benchmark_results.json", "w") as f:
        json.dump(final_output, f, indent=2)
        
    print(f"\nDone! Benchmark saved to benchmark_results.json")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
