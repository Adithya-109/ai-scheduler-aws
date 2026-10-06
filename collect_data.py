import os
import sys
import time
import requests
import subprocess
import pandas as pd
from pipeline.feature_extractor import CodeFeatureExtractor

# TODO: REPLACE WITH YOUR ACTUAL EC2 PUBLIC IP ADDRESS
CLOUD_WORKER_URL = "http://18.60.146.38:8000/execute"

def run_benchmark(script_path):
    with open(script_path, 'r') as f:
        code_str = f.read()

    # 1. Extract AST Features
    extractor = CodeFeatureExtractor()
    features = extractor.analyze(code_str)
    
    if "error" in features:
        return None

    # 2. Measure actual Edge hardware execution time
    start_edge = time.perf_counter()
    subprocess.run([sys.executable, script_path], capture_output=True)
    features['actual_edge_time'] = time.perf_counter() - start_edge

    # 3. Request actual Cloud hardware execution time
    try:
        response = requests.post(CLOUD_WORKER_URL, json={"code": code_str}, timeout=60)
        if response.status_code == 200:
            cloud_data = response.json()
            # We specifically want internal compute time, without the network travel delay
            features['actual_cloud_time'] = cloud_data.get('execution_time_seconds', 0.0)
        else:
            print(f"Cloud execution failed for {script_path}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Failed to connect to Cloud worker for {script_path}: {e}")
        return None

    return features

if __name__ == "__main__":
    print(f"Starting true hardware profiling across Edge and Cloud...")
    print(f"Targeting Cloud Node: {CLOUD_WORKER_URL}")
    
    data = []
    script_files = [f for f in os.listdir("test_scripts") if f.endswith(".py")]
    
    for i, file in enumerate(script_files):
        print(f"Benchmarking {file} ({i+1}/{len(script_files)})...")
        result = run_benchmark(os.path.join("test_scripts", file))
        if result:
            data.append(result)
            
    if data:
        df = pd.DataFrame(data)
        df.to_csv("hardware_benchmark.csv", index=False)
        print(f"\nSuccess! Built empirical dataset with {len(data)} true hardware profiles.")
    else:
        print("\nFailed to collect data. Ensure your EC2 worker is running and IP is correct.")