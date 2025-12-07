#!/usr/bin/env python3
"""
Generate realistic 5-minute demo data for Heimr.ai website.
Scenario: Memory Pressure / GC Pauses causing latency spikes.
"""
import csv
import json
import random
import uuid
from datetime import datetime, timedelta

# Configuration
DURATION_MINUTES = 5
REQUESTS_PER_SECOND = 10
START_TIME = datetime(2025, 12, 7, 10, 0, 0)  # 10:00:00 AM
START_TIMESTAMP_MS = int(START_TIME.timestamp() * 1000)
START_TIMESTAMP_NS = int(START_TIME.timestamp() * 1e9)

ENDPOINTS = [
    "/api/orders",
    "/api/users",
    "/api/products",
    "/api/checkout",
    "/api/inventory"
]

# GC pause events (when they occur in the 5-minute window, in seconds)
GC_EVENTS = [45, 95, 140, 185, 220, 265, 290]  # 7 GC pauses


def generate_jmeter_data():
    """Generate JMeter CSV with realistic GC-induced latency spikes."""
    rows = []
    total_seconds = DURATION_MINUTES * 60
    request_interval_ms = 1000 // REQUESTS_PER_SECOND  # 100ms between requests
    
    current_ms = START_TIMESTAMP_MS
    
    for i in range(total_seconds * REQUESTS_PER_SECOND):
        elapsed_seconds = i // REQUESTS_PER_SECOND
        
        # Check if we're in a GC pause window (within 2 seconds of a GC event)
        in_gc_window = any(abs(elapsed_seconds - gc_time) <= 2 for gc_time in GC_EVENTS)
        
        if in_gc_window and random.random() < 0.3:  # 30% chance of slow request during GC
            elapsed = random.randint(3000, 5000)  # 3-5 second latency during GC
        else:
            elapsed = random.randint(80, 150)  # Normal latency
        
        endpoint = random.choice(ENDPOINTS)
        thread_num = (i % 5) + 1
        
        row = {
            "timeStamp": current_ms,
            "elapsed": elapsed,
            "label": f"HTTP Request - {endpoint}",
            "responseCode": "200",
            "responseMessage": "OK",
            "threadName": f"Thread Group 1-{thread_num}",
            "dataType": "text",
            "success": "true",
            "failureMessage": "",
            "bytes": random.randint(1024, 4096),
            "sentBytes": random.randint(256, 512),
            "grpThreads": 5,
            "allThreads": 5,
            "URL": f"http://api.demo.com{endpoint}",
            "Latency": elapsed,
            "IdleTime": 0,
            "Connect": random.randint(1, 10)
        }
        rows.append(row)
        current_ms += request_interval_ms + random.randint(-20, 20)  # Slight jitter
    
    return rows


def generate_prometheus_metrics():
    """Generate Prometheus metrics showing memory growth and CPU spikes."""
    cpu_values = []
    memory_values = []
    
    sample_interval = 15  # seconds
    num_samples = (DURATION_MINUTES * 60) // sample_interval
    
    base_memory = 200_000_000  # 200MB starting
    memory_growth_rate = 2_000_000  # 2MB per sample (memory leak simulation)
    
    current_ts = int(START_TIME.timestamp())
    current_memory = base_memory
    
    for i in range(num_samples):
        elapsed_seconds = i * sample_interval
        
        # Check if near GC event
        near_gc = any(abs(elapsed_seconds - gc_time) <= sample_interval for gc_time in GC_EVENTS)
        
        # CPU: base 15%, spike to 60-80% during GC
        if near_gc:
            cpu = random.uniform(0.55, 0.80)
        else:
            cpu = random.uniform(0.12, 0.25)
        
        cpu_values.append([current_ts, f"{cpu:.6f}"])
        
        # Memory: steady growth with slight drops after GC
        if near_gc:
            current_memory -= random.randint(30_000_000, 50_000_000)  # GC frees some memory
            current_memory = max(current_memory, base_memory)
        else:
            current_memory += memory_growth_rate + random.randint(-500_000, 500_000)
        
        memory_values.append([current_ts, str(int(current_memory))])
        current_ts += sample_interval
    
    return {
        "cpu_usage": [{
            "metric": {"pod": "ecommerce-api-pod"},
            "values": cpu_values
        }],
        "memory_usage": [{
            "metric": {"pod": "ecommerce-api-pod"},
            "values": memory_values
        }]
    }


def generate_loki_logs():
    """Generate Loki logs with GC pause warnings."""
    values = []
    
    log_interval_seconds = 5
    num_logs = (DURATION_MINUTES * 60) // log_interval_seconds
    
    current_ts_ns = START_TIMESTAMP_NS
    gc_warning_count = 0
    
    for i in range(num_logs):
        elapsed_seconds = i * log_interval_seconds
        
        # Check if in GC window
        in_gc_window = any(abs(elapsed_seconds - gc_time) <= 5 for gc_time in GC_EVENTS)
        
        if in_gc_window and gc_warning_count < len(GC_EVENTS):
            # GC warning log
            pause_duration = random.randint(1200, 2500)
            total_duration = random.randint(3500, 5000)
            log_line = f'level=warn msg="GC pause detected" pause_duration={pause_duration}ms total_duration={total_duration}ms heap_before="{random.randint(600, 800)}MB" heap_after="{random.randint(200, 350)}MB" scenario="memory-pressure-demo"'
            gc_warning_count += 1
        else:
            # Normal request log
            duration = random.randint(80, 150)
            endpoint = random.choice(ENDPOINTS)
            log_line = f'level=info msg="Request processed" duration={duration}ms status=200 endpoint="{endpoint}" scenario="memory-pressure-demo"'
        
        values.append([str(current_ts_ns), log_line])
        current_ts_ns += log_interval_seconds * int(1e9)
    
    return {
        "status": "success",
        "data": {
            "resultType": "streams",
            "result": [{
                "stream": {
                    "app": "ecommerce-api",
                    "namespace": "demo",
                    "scenario": "memory-pressure"
                },
                "values": values
            }]
        }
    }


def generate_tempo_traces():
    """Generate Tempo traces with some slow spans during GC events."""
    traces = []
    
    # Generate 20 traces total, some slow during GC events
    trace_times = [START_TIME + timedelta(seconds=random.randint(0, DURATION_MINUTES*60-1)) 
                   for _ in range(20)]
    trace_times.sort()
    
    for i, trace_time in enumerate(trace_times):
        elapsed_seconds = (trace_time - START_TIME).total_seconds()
        
        # Check if near GC event
        near_gc = any(abs(elapsed_seconds - gc_time) <= 5 for gc_time in GC_EVENTS)
        
        trace_id = uuid.uuid4().hex
        span_id = uuid.uuid4().hex[:16]
        
        if near_gc and random.random() < 0.5:
            duration = random.randint(3500000, 5000000)  # 3.5-5 seconds in microseconds
            status_code = 200
        else:
            duration = random.randint(80000, 150000)  # 80-150ms in microseconds
            status_code = 200
        
        endpoint = random.choice(ENDPOINTS)
        
        trace = {
            "traceID": trace_id,
            "spans": [{
                "traceID": trace_id,
                "spanID": span_id,
                "operationName": f"HTTP GET {endpoint}",
                "startTime": int(trace_time.timestamp() * 1e6),
                "duration": duration,
                "tags": [
                    {"key": "http.method", "value": "GET"},
                    {"key": "http.url", "value": f"http://api.demo.com{endpoint}"},
                    {"key": "http.status_code", "value": status_code},
                    {"key": "service.name", "value": "ecommerce-api"},
                    {"key": "span.kind", "value": "server"}
                ]
            }]
        }
        
        # Add child span for slow requests (database call)
        if duration > 1000000:  # If slow, add DB span
            db_span_id = uuid.uuid4().hex[:16]
            trace["spans"].append({
                "traceID": trace_id,
                "spanID": db_span_id,
                "parentSpanID": span_id,
                "operationName": "PostgreSQL query",
                "startTime": int(trace_time.timestamp() * 1e6) + 50000,
                "duration": duration - 100000,  # Most time in DB
                "tags": [
                    {"key": "db.type", "value": "postgresql"},
                    {"key": "db.statement", "value": "SELECT * FROM orders WHERE..."},
                    {"key": "db.instance", "value": "postgres-primary"},
                    {"key": "gc.pause.affected", "value": "true"}
                ]
            })
        
        traces.append(trace)
    
    return {"data": traces}


def main():
    output_dir = "/home/lostborion/Heimr.ai/website/demo"
    
    print("Generating JMeter demo data...")
    jmeter_data = generate_jmeter_data()
    with open(f"{output_dir}/jmeter_demo.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(jmeter_data[0].keys()))
        writer.writeheader()
        writer.writerows(jmeter_data)
    print(f"  Created jmeter_demo.csv with {len(jmeter_data)} requests")
    
    print("Generating Prometheus demo metrics...")
    prom_data = generate_prometheus_metrics()
    with open(f"{output_dir}/prometheus_demo.json", "w") as f:
        json.dump(prom_data, f, indent=2)
    print(f"  Created prometheus_demo.json with {len(prom_data['cpu_usage'][0]['values'])} samples")
    
    print("Generating Loki demo logs...")
    loki_data = generate_loki_logs()
    with open(f"{output_dir}/loki_demo.json", "w") as f:
        json.dump(loki_data, f, indent=2)
    print(f"  Created loki_demo.json with {len(loki_data['data']['result'][0]['values'])} logs")
    
    print("Generating Tempo demo traces...")
    tempo_data = generate_tempo_traces()
    with open(f"{output_dir}/tempo_demo.json", "w") as f:
        json.dump(tempo_data, f, indent=2)
    print(f"  Created tempo_demo.json with {len(tempo_data['data'])} traces")
    
    print("\n✅ All demo data generated successfully!")


if __name__ == "__main__":
    main()
