import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def generate_jtl(filename, duration_min=10, requests_per_sec=10, scenario="normal"):
    """
    Generates a JTL file with specific characteristics.
    """
    start_time = datetime.now()
    total_requests = duration_min * 60 * requests_per_sec
    
    timestamps = [start_time + timedelta(seconds=i/requests_per_sec) for i in range(total_requests)]
    
    # Base latency: Normal distribution
    latencies = np.random.normal(loc=200, scale=50, size=total_requests)
    response_codes = [200] * total_requests
    successes = [True] * total_requests
    
    if scenario == "latency_spike":
        # Inject a spike in the middle
        mid_point = total_requests // 2
        spike_duration = requests_per_sec * 60 # 1 minute spike
        latencies[mid_point:mid_point+spike_duration] += 2000 # Add 2s latency
        
    elif scenario == "error_burst":
        # Inject errors
        mid_point = total_requests // 2
        burst_duration = requests_per_sec * 30 # 30s burst
        for i in range(mid_point, mid_point+burst_duration):
            response_codes[i] = 500
            successes[i] = False
            
    elif scenario == "memory_leak":
        # Gradual increase
        increase = np.linspace(0, 1000, total_requests)
        latencies += increase

    # Ensure no negative latencies
    latencies = np.maximum(latencies, 10)
    
    df = pd.DataFrame({
        'timeStamp': [int(ts.timestamp() * 1000) for ts in timestamps],
        'elapsed': latencies.astype(int),
        'label': ['Request'] * total_requests,
        'responseCode': response_codes,
        'responseMessage': ['OK' if s else 'Internal Server Error' for s in successes],
        'threadName': ['Thread Group 1-1'] * total_requests,
        'dataType': ['text'] * total_requests,
        'success': successes,
        'failureMessage': ['' for _ in successes],
        'bytes': [1024] * total_requests,
        'sentBytes': [512] * total_requests,
        'grpThreads': [10] * total_requests,
        'allThreads': [10] * total_requests,
        'URL': ['http://example.com/api'] * total_requests,
        'Latency': latencies.astype(int) - 10, # Mock network latency
        'IdleTime': [0] * total_requests,
        'Connect': [10] * total_requests
    })
    
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    df.to_csv(filename, index=False)
    print(f"Generated {filename} ({scenario})")

if __name__ == "__main__":
    generate_jtl("tests/data/scenario_normal.jtl", scenario="normal")
    generate_jtl("tests/data/scenario_spike.jtl", scenario="latency_spike")
    generate_jtl("tests/data/scenario_errors.jtl", scenario="error_burst")
    generate_jtl("tests/data/scenario_leak.jtl", scenario="memory_leak")
