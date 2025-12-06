# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

import os
import re
import csv
import json
import random
import time
from datetime import datetime, timedelta

# Configuration
OUTPUT_DIR = "data/mocks"
SCENARIOS_FILE = "FAILURE_SCENARIOS.md"

def parse_scenarios(filepath):
    """
    Parses the markdown file to extract scenarios.
    Returns a list of dicts: {'id': 'API-001', 'name': '...', 'pattern': '...'}
    """
    scenarios = []
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # Regex to match table rows: | `ID` | **Name** | Description | Metrics Pattern | ...
    # Example: | `API-002` | **Latency Spike (Tail)** | ... | Spike in p99, stable p50. | ...
    row_pattern = re.compile(r'\|\s*`([^`]+)`\s*\|\s*\*\*([^*]+)\*\*\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|')

    for line in lines:
        match = row_pattern.search(line)
        if match:
            scenarios.append({
                'id': match.group(1).strip(),
                'name': match.group(2).strip(),
                'description': match.group(3).strip(),
                'metrics_pattern': match.group(4).strip()
            })
    return scenarios

def generate_jmeter_csv(scenario, output_path):
    """Generates scenario-specific JMeter JTL (CSV) file."""
    headers = ["timeStamp", "elapsed", "label", "responseCode", "responseMessage", "threadName", "dataType", "success", "failureMessage", "bytes", "sentBytes", "grpThreads", "allThreads", "URL", "Latency", "IdleTime", "Connect"]
    
    start_time = int(time.time() * 1000)
    records = []
    
    sid = scenario['id']
    name = scenario['name']
    
    # Generate scenario-specific latency patterns
    for i in range(100):
        ts = start_time + (i * 100)
        
        # Default values
        code = 200
        success = "true"
        msg = "OK"
        
        # Scenario-specific latency and error patterns
        if sid == "API-001":  # Healthy Baseline
            # Very tight range to avoid false positives
            elapsed = random.randint(100, 120)
        
        elif "Latency Spike" in name or "Tail" in name:
            # 10% extreme spikes (tail latency)
            if random.random() > 0.9:
                elapsed = random.randint(3000, 5000)
            else:
                elapsed = random.randint(80, 150)
        
        elif "Global Latency" in name:
            # All requests slow
            elapsed = random.randint(800, 1500)
        
        elif "Bimodal" in name:
            # 40% slow (cache miss), 60% fast (cache hit)
            if random.random() > 0.6:
                elapsed = random.randint(3000, 5000)  # Cache miss
            else:
                elapsed = random.randint(80, 150)  # Cache hit
        
        elif "Memory Leak" in name or "OOM" in name:
            # Gradual latency increase as memory fills
            base = 100
            growth = int(i * 30)  # Grows with each request
            elapsed = base + growth + random.randint(-20, 20)
        
        elif "CPU Saturation" in name or "CPU" in name:
            # Sudden spike after warmup
            if i > 70:
                elapsed = random.randint(2000, 5000)
            else:
                elapsed = random.randint(80, 150)
        
        elif "Rate Limiting" in name or "429" in name:
            # Periodic rate limit hits
            if i % 10 == 0:
                elapsed = random.randint(5000, 10000)
                code = 429
                success = "false"
                msg = "Too Many Requests"
            else:
                elapsed = random.randint(80, 150)
        
        elif "Error" in name or "5xx" in scenario['metrics_pattern']:
            # 30% errors
            if random.random() > 0.7:
                elapsed = random.randint(100, 500)
                code = 500
                success = "false"
                msg = "Internal Server Error"
            else:
                elapsed = random.randint(80, 150)
        
        elif "Thread Starvation" in name or "Blocking" in name:
            # Increasing latency as threads get exhausted
            if i > 50:
                elapsed = random.randint(2000, 8000)
            else:
                elapsed = random.randint(100, 300)
        
        elif "Large Payload" in name:
            # Consistently high latency
            elapsed = random.randint(800, 2000)
        
        elif "Database" in name or "DB" in sid or "Slow Query" in name:
            # 20% very slow queries
            if random.random() > 0.8:
                elapsed = random.randint(5000, 10000)
            else:
                elapsed = random.randint(100, 300)
        
        elif "Cache" in name:
            # Cache stampede/avalanche - periodic spikes
            if i % 15 == 0:
                elapsed = random.randint(3000, 6000)
            else:
                elapsed = random.randint(80, 150)
        
        elif "Timeout" in name or "Stall" in name:
            # Some requests timeout
            if random.random() > 0.85:
                elapsed = random.randint(10000, 30000)
                code = 504
                success = "false"
                msg = "Gateway Timeout"
            else:
                elapsed = random.randint(100, 300)
        
        elif "Cold Start" in name:
            # First few requests very slow
            if i < 5:
                elapsed = random.randint(3000, 8000)
            else:
                elapsed = random.randint(100, 300)
        
        else:
            # Generic failure pattern - some latency spikes
            if random.random() > 0.85:
                elapsed = random.randint(2000, 5000)
            else:
                elapsed = random.randint(100, 300)
        
        records.append([ts, elapsed, "HTTP Request", code, msg, "Thread Group 1-1", "text", success, "", 1024, 0, 1, 1, "http://example.com/api", elapsed, 0, 0])

    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(records)

def generate_k6_json(scenario, output_path):
    """Generates a k6 JSON output file."""
    start_time = datetime.now()
    
    is_latency = "Latency" in scenario['name'] or "Latency" in scenario['metrics_pattern']
    is_error = "Error" in scenario['name'] or "Error" in scenario['metrics_pattern']
    
    with open(output_path, 'w') as f:
        for i in range(100):
            current_time = start_time + timedelta(milliseconds=i*100)
            
            if is_latency and random.random() > 0.8:
                elapsed = random.randint(1000, 5000)
            else:
                elapsed = random.randint(50, 200)
            
            if is_error and random.random() > 0.8:
                status = 500
            else:
                status = 200
                
            record = {
                "type": "Point",
                "metric": "http_req_duration",
                "data": {
                    "time": current_time.isoformat() + "Z",
                    "value": float(elapsed),
                    "tags": {
                        "status": str(status),
                        "name": "http://example.com/api"
                    }
                }
            }
            f.write(json.dumps(record) + "\n")

def generate_gatling_log(scenario, output_path):
    """Generates a Gatling simulation.log file."""
    # Format: REQUEST <ScenarioName> <UserId> <RequestName> <StartTimestamp> <EndTimestamp> <Status> <Message>
    
    start_time = int(time.time() * 1000)
    
    is_latency = "Latency" in scenario['name'] or "Latency" in scenario['metrics_pattern']
    is_error = "Error" in scenario['name'] or "Error" in scenario['metrics_pattern']
    
    with open(output_path, 'w') as f:
        f.write("RUN\tSimulation\tuser\tSTART\t" + str(start_time) + "\n")
        
        for i in range(100):
            req_start = start_time + (i * 100)
            
            if is_latency and random.random() > 0.8:
                duration = random.randint(1000, 5000)
            else:
                duration = random.randint(50, 200)
            
            req_end = req_start + duration
            
            if is_error and random.random() > 0.8:
                status = "KO"
                msg = "Internal Server Error"
            else:
                status = "OK"
                msg = ""
                
            # REQUEST <Scenario> <User> <Request> <Start> <End> <Status> <Msg>
            line = f"REQUEST\tScenario1\t1\tRequest1\t{req_start}\t{req_end}\t{status}\t{msg}\n"
            f.write(line)

def generate_locust_csv(scenario, output_path):
    """Generates a Locust _stats_history.csv file."""
    # Timestamp,User Count,Type,Name,Requests/s,Failures/s,50%,...,Total Average Response Time,...
    headers = ["Timestamp", "User Count", "Type", "Name", "Requests/s", "Failures/s", "50%", "66%", "75%", "80%", "90%", "95%", "98%", "99%", "99.9%", "99.99%", "100%", "Total Request Count", "Total Failure Count", "Total Median Response Time", "Total Average Response Time", "Total Min Response Time", "Total Max Response Time", "Total Average Content Size"]
    
    start_time = int(time.time())
    records = []
    
    is_latency = "Latency" in scenario['name'] or "Latency" in scenario['metrics_pattern']
    is_error = "Error" in scenario['name'] or "Error" in scenario['metrics_pattern']
    
    for i in range(10): # 10 seconds of data
        ts = start_time + i
        
        if is_latency:
            avg_resp = random.randint(500, 2000)
        else:
            avg_resp = random.randint(50, 150)
            
        if is_error:
            failures = random.randint(1, 10)
        else:
            failures = 0
            
        # Simplified data
        records.append([ts, 10, "GET", "/api", 10, failures, avg_resp, avg_resp, avg_resp, avg_resp, avg_resp, avg_resp, avg_resp, avg_resp, avg_resp, avg_resp, avg_resp, (i+1)*10, failures, avg_resp, avg_resp, avg_resp, avg_resp, 100])

    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(records)

def generate_loki_logs(scenario, output_path):
    """Generates scenario-specific Loki logs."""
    sid = scenario['id']
    name = scenario['name']
    
    logs = []
    start_time_ns = int(time.time() * 1e9)
    
    # Scenario-specific log patterns
    if sid == "API-001":  # Healthy Baseline
        for i in range(20):
            ts = str(start_time_ns + (i * 100000000))
            line = f"level=info msg=\"Request processed\" duration={random.randint(80, 150)}ms status=200 scenario=\"{sid}\""
            logs.append([ts, line])
    
    elif "Latency Spike" in name or "Bimodal" in name:
        for i in range(20):
            ts = str(start_time_ns + (i * 100000000))
            if random.random() > 0.7:  # 30% slow requests
                if "Bimodal" in name:
                    line = f"level=warn msg=\"Cache miss\" key=user:{random.randint(1000,9999)} fallback=database duration={random.randint(3000,5000)}ms scenario=\"{sid}\""
                else:
                    line = f"level=warn msg=\"GC pause detected\" pause_duration={random.randint(500,2000)}ms total_duration={random.randint(1000,5000)}ms scenario=\"{sid}\""
            else:
                line = f"level=info msg=\"Request processed\" duration={random.randint(80,150)}ms status=200 scenario=\"{sid}\""
            logs.append([ts, line])
    
    elif "Error" in name or "5xx" in scenario['metrics_pattern']:
        for i in range(20):
            ts = str(start_time_ns + (i * 100000000))
            if random.random() > 0.7:  # 30% errors
                errors = [
                    "Database connection timeout",
                    "Downstream service unavailable",
                    "Internal server error: NullPointerException",
                    "Service temporarily unavailable"
                ]
                line = f"level=error msg=\"Request failed\" error=\"{random.choice(errors)}\" status=500 scenario=\"{sid}\""
            else:
                line = f"level=info msg=\"Request processed\" duration={random.randint(80,150)}ms status=200 scenario=\"{sid}\""
            logs.append([ts, line])
    
    elif "Memory Leak" in name or "OOM" in name:
        for i in range(20):
            ts = str(start_time_ns + (i * 100000000))
            mem_mb = 200 + (i * 50)  # Growing memory
            if i > 15:
                line = f"level=warn msg=\"High memory usage\" heap_used={mem_mb}MB heap_max=1024MB gc_count={i} scenario=\"{sid}\""
            else:
                line = f"level=info msg=\"Request processed\" heap_used={mem_mb}MB duration={random.randint(80,150)}ms scenario=\"{sid}\""
            logs.append([ts, line])
    
    elif "CPU" in name:
        for i in range(20):
            ts = str(start_time_ns + (i * 100000000))
            if i > 10:
                line = f"level=error msg=\"CPU saturation\" cpu_usage=98% thread_count=500 scenario=\"{sid}\""
            else:
                line = f"level=info msg=\"Request processed\" cpu_usage={random.randint(10,30)}% duration={random.randint(80,150)}ms scenario=\"{sid}\""
            logs.append([ts, line])
    
    elif "Cache" in name:
        for i in range(20):
            ts = str(start_time_ns + (i * 100000000))
            if random.random() > 0.5:  # 50% cache issues
                line = f"level=warn msg=\"Cache miss\" key=session:{random.randint(1000,9999)} hit_rate=0.45 scenario=\"{sid}\""
            else:
                line = f"level=info msg=\"Cache hit\" key=session:{random.randint(1000,9999)} hit_rate=0.92 scenario=\"{sid}\""
            logs.append([ts, line])
    
    elif "Database" in name or "DB" in sid:
        for i in range(20):
            ts = str(start_time_ns + (i * 100000000))
            if "Slow Query" in name:
                line = f"level=warn msg=\"Slow query detected\" query=\"SELECT * FROM users WHERE...\" duration={random.randint(2000,8000)}ms rows_scanned=1000000 scenario=\"{sid}\""
            elif "Connection Pool" in name:
                line = f"level=error msg=\"Connection pool exhausted\" active=50 max=50 waiting={random.randint(10,100)} scenario=\"{sid}\""
            elif "Deadlock" in name:
                line = f"level=error msg=\"Deadlock detected\" transaction_id={random.randint(1000,9999)} victim=true scenario=\"{sid}\""
            else:
                line = f"level=info msg=\"Query executed\" duration={random.randint(10,50)}ms scenario=\"{sid}\""
            logs.append([ts, line])
    
    else:
        # Generic logs for other scenarios
        for i in range(20):
            ts = str(start_time_ns + (i * 100000000))
            line = f"level=info msg=\"Request processed\" duration={random.randint(80,200)}ms scenario=\"{sid}\""
            logs.append([ts, line])
    
    data = {
        "status": "success",
        "data": {
            "resultType": "streams",
            "result": [{
                "stream": {"app": "chaos-test", "scenario": sid},
                "values": logs
            }]
        }
    }
    
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

def generate_tempo_traces(scenario, output_path):
    """Generates scenario-specific Tempo traces with detailed spans."""
    sid = scenario['id']
    name = scenario['name']
    
    traces = []
    
    for i in range(5):
        trace_id = f"{random.getrandbits(128):032x}"
        start_time_us = int(time.time() * 1e6)
        
        # Create spans based on scenario
        spans = []
        
        if "Bimodal" in name or "Cache" in name:
            # Show cache hit vs miss paths
            if random.random() > 0.6:  # 40% cache hits (fast)
                # Fast path: cache hit
                root_span_id = f"{random.getrandbits(64):016x}"
                cache_span_id = f"{random.getrandbits(64):016x}"
                
                root_duration = random.randint(100000, 200000)  # 100-200ms
                cache_duration = random.randint(5000, 10000)  # 5-10ms
                
                spans.append({
                    "traceID": trace_id,
                    "spanID": root_span_id,
                    "operationName": "HTTP GET /api",
                    "startTime": start_time_us,
                    "duration": root_duration,
                    "tags": [
                        {"key": "http.method", "value": "GET"},
                        {"key": "http.status_code", "value": 200}
                    ]
                })
                
                spans.append({
                    "traceID": trace_id,
                    "spanID": cache_span_id,
                    "parentSpanID": root_span_id,
                    "operationName": "redis.get",
                    "startTime": start_time_us + 10000,
                    "duration": cache_duration,
                    "tags": [
                        {"key": "cache.hit", "value": True},
                        {"key": "cache.key", "value": f"user:{random.randint(1000,9999)}"}
                    ]
                })
            else:  # Cache miss (slow)
                root_span_id = f"{random.getrandbits(64):016x}"
                cache_span_id = f"{random.getrandbits(64):016x}"
                db_span_id = f"{random.getrandbits(64):016x}"
                
                root_duration = random.randint(3000000, 5000000)  # 3-5s
                cache_duration = random.randint(5000, 10000)  # 5-10ms
                db_duration = random.randint(2500000, 4500000)  # 2.5-4.5s
                
                spans.append({
                    "traceID": trace_id,
                    "spanID": root_span_id,
                    "operationName": "HTTP GET /api",
                    "startTime": start_time_us,
                    "duration": root_duration,
                    "tags": [
                        {"key": "http.method", "value": "GET"},
                        {"key": "http.status_code", "value": 200}
                    ]
                })
                
                spans.append({
                    "traceID": trace_id,
                    "spanID": cache_span_id,
                    "parentSpanID": root_span_id,
                    "operationName": "redis.get",
                    "startTime": start_time_us + 10000,
                    "duration": cache_duration,
                    "tags": [
                        {"key": "cache.hit", "value": False},
                        {"key": "cache.key", "value": f"user:{random.randint(1000,9999)}"}
                    ]
                })
                
                spans.append({
                    "traceID": trace_id,
                    "spanID": db_span_id,
                    "parentSpanID": root_span_id,
                    "operationName": "postgres.query",
                    "startTime": start_time_us + 20000,
                    "duration": db_duration,
                    "tags": [
                        {"key": "db.statement", "value": "SELECT * FROM users WHERE id = ?"},
                        {"key": "db.rows", "value": 1}
                    ]
                })
        
        elif "Slow Query" in name or "Database" in name:
            root_span_id = f"{random.getrandbits(64):016x}"
            db_span_id = f"{random.getrandbits(64):016x}"
            
            root_duration = random.randint(5000000, 10000000)  # 5-10s
            db_duration = random.randint(4500000, 9500000)  # 4.5-9.5s
            
            spans.append({
                "traceID": trace_id,
                "spanID": root_span_id,
                "operationName": "HTTP GET /api",
                "startTime": start_time_us,
                "duration": root_duration,
                "tags": [
                    {"key": "http.method", "value": "GET"},
                    {"key": "http.status_code", "value": 200}
                ]
            })
            
            spans.append({
                "traceID": trace_id,
                "spanID": db_span_id,
                "parentSpanID": root_span_id,
                "operationName": "postgres.query",
                "startTime": start_time_us + 100000,
                "duration": db_duration,
                "tags": [
                    {"key": "db.statement", "value": "SELECT * FROM users WHERE email LIKE '%@%'"},
                    {"key": "db.rows_scanned", "value": 1000000},
                    {"key": "db.rows_returned", "value": 1},
                    {"key": "slow_query", "value": True}
                ]
            })
        
        elif "Error" in name or "5xx" in scenario['metrics_pattern']:
            root_span_id = f"{random.getrandbits(64):016x}"
            downstream_span_id = f"{random.getrandbits(64):016x}"
            
            root_duration = random.randint(100000, 500000)
            downstream_duration = random.randint(50000, 450000)
            
            spans.append({
                "traceID": trace_id,
                "spanID": root_span_id,
                "operationName": "HTTP GET /api",
                "startTime": start_time_us,
                "duration": root_duration,
                "tags": [
                    {"key": "http.method", "value": "GET"},
                    {"key": "http.status_code", "value": 500},
                    {"key": "error", "value": True}
                ]
            })
            
            spans.append({
                "traceID": trace_id,
                "spanID": downstream_span_id,
                "parentSpanID": root_span_id,
                "operationName": "HTTP POST /downstream-service",
                "startTime": start_time_us + 10000,
                "duration": downstream_duration,
                "tags": [
                    {"key": "http.status_code", "value": 503},
                    {"key": "error", "value": True},
                    {"key": "error.message", "value": "Service Unavailable"}
                ]
            })
        
        else:
            # Generic trace
            root_span_id = f"{random.getrandbits(64):016x}"
            duration_us = random.randint(50000, 200000)
            
            spans.append({
                "traceID": trace_id,
                "spanID": root_span_id,
                "operationName": "HTTP GET /api",
                "startTime": start_time_us,
                "duration": duration_us,
                "tags": [
                    {"key": "http.method", "value": "GET"},
                    {"key": "http.status_code", "value": 200}
                ]
            })
        
        traces.append({"traceID": trace_id, "spans": spans})
    
    with open(output_path, 'w') as f:
        json.dump({"data": traces}, f, indent=2)

def generate_prometheus_metrics(scenario, output_path):
    """Generates scenario-specific Prometheus metrics."""
    sid = scenario['id']
    name = scenario['name']
    
    start_time = int(time.time())
    metrics_data = {}
    
    # CPU Usage
    cpu_values = []
    for i in range(20):
        ts = start_time + (i * 15)
        if "CPU Saturation" in name:
            val = str(random.uniform(0.95, 1.0)) if i > 10 else str(random.uniform(0.6, 0.8))
        elif "Memory Leak" in name or "OOM" in name:
            val = str(random.uniform(0.3, 0.5))  # Normal CPU during memory leak
        else:
            val = str(random.uniform(0.05, 0.2))
        cpu_values.append([ts, val])
    
    metrics_data['cpu_usage'] = [{"metric": {"pod": "chaos-test-pod"}, "values": cpu_values}]
    
    # Memory Usage
    mem_values = []
    for i in range(20):
        ts = start_time + (i * 15)
        if "Memory Leak" in name:
            # Gradual increase
            val = str(int(100 * 1024 * 1024 + (i * 50 * 1024 * 1024)))  # 100MB + 50MB per step
        elif "OOM" in name:
            val = str(int(900 * 1024 * 1024 + (i * 10 * 1024 * 1024)))  # Near limit
        else:
            val = str(random.randint(50 * 1024 * 1024, 200 * 1024 * 1024))
        mem_values.append([ts, val])
    
    metrics_data['memory_usage'] = [{"metric": {"pod": "chaos-test-pod"}, "values": mem_values}]
    
    # Cache-specific metrics
    if "Cache" in name or "Bimodal" in name:
        cache_hit_rate = []
        for i in range(20):
            ts = start_time + (i * 15)
            if "Stampede" in name or "Avalanche" in name:
                rate = str(random.uniform(0.1, 0.3))  # Low hit rate
            elif "Bimodal" in name:
                rate = str(random.uniform(0.4, 0.6))  # Medium hit rate
            else:
                rate = str(random.uniform(0.85, 0.95))  # Normal
            cache_hit_rate.append([ts, rate])
        
        metrics_data['cache_hit_rate'] = [{"metric": {"cache": "redis"}, "values": cache_hit_rate}]
    
    # Database-specific metrics
    if "Database" in name or "DB" in sid or "Slow Query" in name:
        db_query_duration = []
        for i in range(20):
            ts = start_time + (i * 15)
            if "Slow Query" in name:
                duration = str(random.uniform(2.0, 8.0))  # 2-8 seconds
            else:
                duration = str(random.uniform(0.01, 0.05))  # 10-50ms
            db_query_duration.append([ts, duration])
        
        metrics_data['db_query_duration_seconds'] = [{"metric": {"database": "postgres"}, "values": db_query_duration}]
    
    with open(output_path, 'w') as f:
        json.dump(metrics_data, f, indent=2)

def main():
    if not os.path.exists(SCENARIOS_FILE):
        print(f"Error: {SCENARIOS_FILE} not found.")
        return

    scenarios = parse_scenarios(SCENARIOS_FILE)
    print(f"Found {len(scenarios)} scenarios.")
    
    for scenario in scenarios:
        sid = scenario['id']
        sname = scenario['name']
        
        # Create directory
        scenario_dir = os.path.join(OUTPUT_DIR, sid)
        os.makedirs(scenario_dir, exist_ok=True)
        
        print(f"Generating mocks for {sid}: {sname}")
        
        # Generate files
        generate_jmeter_csv(scenario, os.path.join(scenario_dir, "jmeter_results.csv"))
        generate_k6_json(scenario, os.path.join(scenario_dir, "k6_results.json"))
        generate_gatling_log(scenario, os.path.join(scenario_dir, "simulation.log"))
        generate_locust_csv(scenario, os.path.join(scenario_dir, "locust_stats_history.csv"))
        generate_loki_logs(scenario, os.path.join(scenario_dir, "loki_logs.json"))
        generate_tempo_traces(scenario, os.path.join(scenario_dir, "tempo_traces.json"))
        generate_prometheus_metrics(scenario, os.path.join(scenario_dir, "prometheus_metrics.json"))

    print(f"Done. Mocks generated in {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
