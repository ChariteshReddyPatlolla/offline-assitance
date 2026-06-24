import sys
import json
import time
import requests
import re
import argparse

# The 5 Categories of Tests
TEST_SUITE = [
    {
        "category": "OS Commands",
        "queries": [
            "Open calculator",
            "Open notepad"
        ]
    },
    {
        "category": "File Operations",
        "queries": [
            "Create a file named test_file.txt inside C:\\Users\\patlo\\Desktop\\benchmark_temp with the content 'hello'",
            "Read the file C:\\Users\\patlo\\Desktop\\benchmark_temp\\test_file.txt",
            "Delete the file C:\\Users\\patlo\\Desktop\\benchmark_temp\\test_file.txt"
        ]
    },
    {
        "category": "Browser Automation",
        "queries": [
            "Open browser and go to wikipedia.org",
            "Search for 'Python' on wikipedia.org",
            "Close browser"
        ]
    },
    {
        "category": "Research Tools",
        "queries": [
            "Research the latest news about Artificial Intelligence",
            "Search for Python 3.12 release notes and summarize"
        ]
    },
    {
        "category": "Multi Step Tasks",
        "queries": [
            "Open wikipedia, search for Machine Learning, extract the first paragraph, and save it to C:\\Users\\patlo\\Desktop\\benchmark_temp\\ml.txt"
        ]
    }
]

API_URL = "http://127.0.0.1:8000/api/chat/"
SESSION_ID = "benchmark-action-session"

def send_query(query: str):
    print(f"\n[{time.strftime('%H:%M:%S')}] Sending query: {query}")
    start_time = time.perf_counter()
    try:
        payload = {"session_id": SESSION_ID, "message": query, "user_id": "benchmark_user"}
        response = requests.post(API_URL, json=payload, timeout=120)
        end_time = time.perf_counter()
        if response.status_code == 200:
            data = response.json()
            latency = end_time - start_time
            print(f" -> Success! Response latency: {latency:.3f}s")
            return {"latency": latency, "response": data.get("content", ""), "error": None}
        else:
            print(f" -> Failed! HTTP {response.status_code}")
            return {"latency": end_time - start_time, "error": f"HTTP {response.status_code}", "response": response.text}
    except Exception as e:
        print(f" -> Request Exception: {e}")
        return {"latency": 0, "error": str(e), "response": ""}

def main():
    import os
    os.makedirs(r"C:\Users\patlo\Desktop\benchmark_temp", exist_ok=True)
    
    results = {}
    print("========================================")
    print(" STARTING REAL ACTION MODE BENCHMARK ")
    print("========================================")
    
    for category in TEST_SUITE:
        cat_name = category["category"]
        results[cat_name] = []
        print(f"\n>>> Running Category: {cat_name} <<<")
        for query in category["queries"]:
            res = send_query(query)
            results[cat_name].append({
                "query": query,
                "latency": res["latency"],
                "response": res["response"],
                "error": res["error"]
            })
            time.sleep(2)  # brief pause between real actions to let OS settle
            
    # Save the basic request timing results
    with open("benchmark_action_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)
        
    print("\nBenchmark HTTP suite complete. Check benchmark_action_results.json.")
    print("Ensure you also parse the application stdout logs for the granular BENCHMARK_LOG_JSON| metrics.")

if __name__ == "__main__":
    main()
