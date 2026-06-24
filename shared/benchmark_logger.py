import json
import time
import os

LOG_FILE = r"C:\Users\patlo\Desktop\projects\offline assistance-stage 1\benchmark_metrics.jsonl"

def log_metric(session_id: str, metric_type: str, data: dict):
    """
    Logs an arbitrary metric to a JSON lines file for the benchmark script to parse.
    """
    try:
        entry = {
            "timestamp": time.time(),
            "session_id": session_id,
            "metric_type": metric_type,
            "data": data
        }
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass
