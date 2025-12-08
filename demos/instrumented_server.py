#!/usr/bin/env python3
# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.

"""
Instrumented Demo API Server with Error Injection
Features:
- Prometheus metrics (/metrics)
- Structured JSON logging (for Loki/Promtail)
- OpenTelemetry traces (for Tempo)
- Error injection endpoints (latency, errors, memory leaks)
"""

import os
import sys
import time
import random
import json
import gc
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================
PORT = int(os.environ.get('PORT', 8080))
TEMPO_ENDPOINT = os.environ.get('TEMPO_ENDPOINT', 'http://localhost:4318/v1/traces')

# ============================================================================
# ERROR INJECTION STATE (Global, thread-safe)
# ============================================================================
class InjectionState:
    def __init__(self):
        self.lock = threading.Lock()
        self.latency_ms = 0          # Extra latency to add (ms)
        self.error_rate = 0.0        # Probability of 500 errors (0-1)
        self.memory_leak_mb = 0      # Memory to allocate (MB)
        self.memory_blocks = []      # Allocated memory blocks
        self.cpu_burn_ms = 0         # CPU burn time (ms)
        self.enabled = False
        
    def set_injection(self, latency_ms=0, error_rate=0.0, memory_mb=0, cpu_ms=0):
        with self.lock:
            self.latency_ms = latency_ms
            self.error_rate = error_rate
            self.cpu_burn_ms = cpu_ms
            
            # Handle memory allocation/deallocation
            if memory_mb > self.memory_leak_mb:
                # Allocate more memory
                blocks_to_add = memory_mb - self.memory_leak_mb
                for _ in range(blocks_to_add):
                    self.memory_blocks.append(bytearray(1024 * 1024))  # 1MB blocks
            elif memory_mb < self.memory_leak_mb:
                # Free memory
                blocks_to_remove = self.memory_leak_mb - memory_mb
                for _ in range(min(blocks_to_remove, len(self.memory_blocks))):
                    self.memory_blocks.pop()
                gc.collect()
            
            self.memory_leak_mb = memory_mb
            self.enabled = latency_ms > 0 or error_rate > 0 or memory_mb > 0 or cpu_ms > 0
            
    def get_state(self):
        with self.lock:
            return {
                "enabled": self.enabled,
                "latency_ms": self.latency_ms,
                "error_rate": self.error_rate,
                "memory_leak_mb": self.memory_leak_mb,
                "cpu_burn_ms": self.cpu_burn_ms,
                "memory_blocks_allocated": len(self.memory_blocks)
            }
    
    def apply_injection(self):
        """Apply current injection effects. Returns (should_error, applied_latency_ms)"""
        should_error = False
        applied_latency = 0
        
        with self.lock:
            # Apply latency
            if self.latency_ms > 0:
                delay = self.latency_ms / 1000.0
                time.sleep(delay)
                applied_latency = self.latency_ms
            
            # Apply CPU burn
            if self.cpu_burn_ms > 0:
                end_time = time.time() + (self.cpu_burn_ms / 1000.0)
                while time.time() < end_time:
                    _ = sum(i * i for i in range(1000))
            
            # Check error rate
            if self.error_rate > 0 and random.random() < self.error_rate:
                should_error = True
        
        return should_error, applied_latency

INJECTION = InjectionState()

# ============================================================================
# PROMETHEUS METRICS
# ============================================================================
class PrometheusMetrics:
    def __init__(self):
        self.lock = threading.Lock()
        self.requests_total = {}      # {endpoint: count}
        self.requests_failed = {}     # {endpoint: count}
        self.request_duration_sum = {}  # {endpoint: sum_ms}
        self.request_duration_count = {}
        self.active_requests = 0
        
    def record_request(self, endpoint, status, duration_ms):
        with self.lock:
            # Total requests
            self.requests_total[endpoint] = self.requests_total.get(endpoint, 0) + 1
            
            # Failed requests
            if status >= 400:
                self.requests_failed[endpoint] = self.requests_failed.get(endpoint, 0) + 1
            
            # Duration
            self.request_duration_sum[endpoint] = self.request_duration_sum.get(endpoint, 0) + duration_ms
            self.request_duration_count[endpoint] = self.request_duration_count.get(endpoint, 0) + 1
    
    def inc_active(self):
        with self.lock:
            self.active_requests += 1
    
    def dec_active(self):
        with self.lock:
            self.active_requests -= 1
    
    def export(self):
        with self.lock:
            lines = []
            
            # Requests total
            lines.append("# HELP http_requests_total Total HTTP requests")
            lines.append("# TYPE http_requests_total counter")
            for endpoint, count in self.requests_total.items():
                lines.append(f'http_requests_total{{endpoint="{endpoint}"}} {count}')
            
            # Failed requests
            lines.append("# HELP http_requests_failed_total Failed HTTP requests")
            lines.append("# TYPE http_requests_failed_total counter")
            for endpoint, count in self.requests_failed.items():
                lines.append(f'http_requests_failed_total{{endpoint="{endpoint}"}} {count}')
            
            # Duration histogram (simplified as sum/count)
            lines.append("# HELP http_request_duration_seconds Request duration")
            lines.append("# TYPE http_request_duration_seconds summary")
            for endpoint in self.request_duration_sum:
                sum_val = self.request_duration_sum[endpoint] / 1000.0
                count_val = self.request_duration_count[endpoint]
                lines.append(f'http_request_duration_seconds_sum{{endpoint="{endpoint}"}} {sum_val}')
                lines.append(f'http_request_duration_seconds_count{{endpoint="{endpoint}"}} {count_val}')
            
            # Active requests
            lines.append("# HELP http_active_requests Active HTTP requests")
            lines.append("# TYPE http_active_requests gauge")
            lines.append(f"http_active_requests {self.active_requests}")
            
            # Injection state
            state = INJECTION.get_state()
            lines.append("# HELP injection_enabled Error injection enabled")
            lines.append("# TYPE injection_enabled gauge")
            lines.append(f"injection_enabled {1 if state['enabled'] else 0}")
            
            lines.append("# HELP injection_latency_ms Injected latency in ms")
            lines.append("# TYPE injection_latency_ms gauge")
            lines.append(f"injection_latency_ms {state['latency_ms']}")
            
            lines.append("# HELP injection_memory_mb Allocated memory for leak simulation")
            lines.append("# TYPE injection_memory_mb gauge")
            lines.append(f"injection_memory_mb {state['memory_leak_mb']}")
            
            return "\n".join(lines) + "\n"

METRICS = PrometheusMetrics()

# ============================================================================
# STRUCTURED LOGGING (for Loki)
# ============================================================================
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname.lower(),
            "message": record.getMessage(),
            "logger": record.name,
        }
        if hasattr(record, 'extra'):
            log_obj.update(record.extra)
        return json.dumps(log_obj)

# Setup logging - both stdout and file for Promtail
LOG_FILE = os.environ.get('LOG_FILE', '/tmp/heimr-logs/demo-api.log')

logger = logging.getLogger("demo-api")
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(JSONFormatter())
logger.addHandler(console_handler)

# File handler (for Promtail/Loki)
try:
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)
    print(f"📝 Logging to: {LOG_FILE}")
except Exception as e:
    print(f"⚠️  Could not create log file {LOG_FILE}: {e}")

def log_request(endpoint, method, status, duration_ms, trace_id=None, error=None):
    extra = {
        "endpoint": endpoint,
        "method": method,
        "status": status,
        "duration_ms": duration_ms,
        "service": "demo-api"
    }
    if trace_id:
        extra["trace_id"] = trace_id
    if error:
        extra["error"] = error
    
    record = logging.LogRecord(
        name="demo-api",
        level=logging.ERROR if status >= 500 else (logging.WARNING if status >= 400 else logging.INFO),
        pathname="",
        lineno=0,
        msg=f"{method} {endpoint} -> {status} ({duration_ms}ms)",
        args=(),
        exc_info=None
    )
    record.extra = extra
    logger.handle(record)

# ============================================================================
# OPENTELEMETRY TRACES (for Tempo)
# ============================================================================
import uuid

def generate_trace_id():
    return uuid.uuid4().hex

def generate_span_id():
    return uuid.uuid4().hex[:16]

def send_trace(trace_id, span_id, operation, duration_ms, status, endpoint):
    """Send trace to Tempo via OTLP HTTP"""
    try:
        import urllib.request
        
        now_ns = int(time.time() * 1e9)
        start_ns = now_ns - int(duration_ms * 1e6)
        
        trace_data = {
            "resourceSpans": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "demo-api"}},
                        {"key": "service.version", "value": {"stringValue": "1.0.0"}}
                    ]
                },
                "scopeSpans": [{
                    "scope": {"name": "demo-api"},
                    "spans": [{
                        "traceId": trace_id,
                        "spanId": span_id,
                        "name": operation,
                        "kind": 2,  # SERVER
                        "startTimeUnixNano": str(start_ns),
                        "endTimeUnixNano": str(now_ns),
                        "attributes": [
                            {"key": "http.method", "value": {"stringValue": "GET"}},
                            {"key": "http.url", "value": {"stringValue": endpoint}},
                            {"key": "http.status_code", "value": {"intValue": status}},
                            {"key": "http.duration_ms", "value": {"intValue": duration_ms}}
                        ],
                        "status": {
                            "code": 2 if status >= 400 else 1,  # ERROR or OK
                            "message": "Error" if status >= 400 else "OK"
                        }
                    }]
                }]
            }]
        }
        
        req = urllib.request.Request(
            TEMPO_ENDPOINT,
            data=json.dumps(trace_data).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        urllib.request.urlopen(req, timeout=1)
    except Exception as e:
        pass  # Silently fail if Tempo is unavailable

# ============================================================================
# HTTP HANDLER
# ============================================================================
class InstrumentedHandler(BaseHTTPRequestHandler):
    users = [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"},
        {"id": 3, "name": "Charlie", "email": "charlie@example.com"}
    ]
    
    products = [
        {"id": 1, "name": "Widget Pro", "price": 29.99},
        {"id": 2, "name": "Gadget Plus", "price": 49.99},
        {"id": 3, "name": "Super Tool", "price": 99.99}
    ]
    
    orders = []
    
    def send_json(self, status, data):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        
        start_time = time.time()
        trace_id = generate_trace_id()
        span_id = generate_span_id()
        status = 200
        error_msg = None
        
        METRICS.inc_active()
        
        try:
            # Apply error injection (skip for control endpoints)
            should_error, injected_latency = False, 0
            if path not in ['/health', '/metrics', '/inject', '/inject/status', '/inject/reset']:
                should_error, injected_latency = INJECTION.apply_injection()
            
            if should_error:
                status = 500
                error_msg = "Injected error"
                self.send_json(500, {"error": "Internal Server Error", "injected": True})
                return
            
            # Route handling
            if path == '/health':
                self.send_json(200, {"status": "healthy", "timestamp": time.time()})
            
            elif path == '/metrics':
                metrics_output = METRICS.export()
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(metrics_output.encode())
            
            elif path == '/inject':
                # Get injection parameters
                latency = int(query.get('latency', [0])[0])
                error_rate = float(query.get('error_rate', [0])[0])
                memory = int(query.get('memory', [0])[0])
                cpu = int(query.get('cpu', [0])[0])
                
                INJECTION.set_injection(latency, error_rate, memory, cpu)
                state = INJECTION.get_state()
                
                log_request("/inject", "GET", 200, 0, trace_id, 
                           f"Injection updated: latency={latency}ms error_rate={error_rate} memory={memory}MB cpu={cpu}ms")
                
                self.send_json(200, {"message": "Injection updated", "state": state})
            
            elif path == '/inject/status':
                self.send_json(200, INJECTION.get_state())
            
            elif path == '/inject/reset':
                INJECTION.set_injection(0, 0, 0, 0)
                self.send_json(200, {"message": "Injection reset", "state": INJECTION.get_state()})
            
            elif path == '/api/users':
                time.sleep(random.uniform(0.02, 0.1))
                self.send_json(200, {"users": self.users, "count": len(self.users)})
            
            elif path == '/api/products':
                time.sleep(random.uniform(0.05, 0.15))
                self.send_json(200, {"products": self.products, "count": len(self.products)})
            
            elif path == '/api/slow':
                delay = random.uniform(2.0, 5.0)
                time.sleep(delay)
                self.send_json(200, {"message": "Slow response", "delay_ms": int(delay * 1000)})
            
            elif path == '/api/error':
                status = 500
                error_msg = "Intentional error"
                self.send_json(500, {"error": "Internal Server Error", "code": "E500"})
            
            else:
                status = 404
                self.send_json(404, {"error": "Not Found"})
        
        except Exception as e:
            status = 500
            error_msg = str(e)
            self.send_json(500, {"error": "Internal Server Error", "message": str(e)})
        
        finally:
            METRICS.dec_active()
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Record metrics
            METRICS.record_request(path, status, duration_ms)
            
            # Log request
            if path not in ['/metrics']:
                log_request(path, "GET", status, duration_ms, trace_id, error_msg)
            
            # Send trace
            if path not in ['/metrics', '/health']:
                threading.Thread(
                    target=send_trace,
                    args=(trace_id, span_id, f"GET {path}", duration_ms, status, path),
                    daemon=True
                ).start()
    
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        start_time = time.time()
        trace_id = generate_trace_id()
        span_id = generate_span_id()
        status = 200
        error_msg = None
        
        METRICS.inc_active()
        
        try:
            should_error, _ = INJECTION.apply_injection()
            
            if should_error:
                status = 500
                error_msg = "Injected error"
                self.send_json(500, {"error": "Internal Server Error", "injected": True})
                return
            
            if path == '/api/orders':
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length) if content_length else b'{}'
                try:
                    data = json.loads(body)
                except:
                    data = {}
                
                time.sleep(random.uniform(0.1, 0.3))
                
                order = {
                    "id": len(self.orders) + 1,
                    "userId": data.get("userId", 1),
                    "productId": data.get("productId", 1),
                    "quantity": data.get("quantity", 1),
                    "status": "created",
                    "timestamp": time.time()
                }
                self.orders.append(order)
                status = 201
                self.send_json(201, {"order": order, "message": "Order created"})
            
            else:
                status = 404
                self.send_json(404, {"error": "Not Found"})
        
        except Exception as e:
            status = 500
            error_msg = str(e)
            self.send_json(500, {"error": str(e)})
        
        finally:
            METRICS.dec_active()
            duration_ms = int((time.time() - start_time) * 1000)
            METRICS.record_request(path, status, duration_ms)
            log_request(path, "POST", status, duration_ms, trace_id, error_msg)
            
            threading.Thread(
                target=send_trace,
                args=(trace_id, span_id, f"POST {path}", duration_ms, status, path),
                daemon=True
            ).start()
    
    def log_message(self, format, *args):
        pass  # Suppress default logging

# ============================================================================
# MAIN
# ============================================================================
def run_server(port=8080):
    server = HTTPServer(('0.0.0.0', port), InstrumentedHandler)
    print(f"🚀 Instrumented Demo API running on http://localhost:{port}")
    print(f"   📊 Prometheus metrics: http://localhost:{port}/metrics")
    print(f"   💉 Error injection:    http://localhost:{port}/inject?latency=500&error_rate=0.1&memory=50")
    print(f"   🔍 Injection status:   http://localhost:{port}/inject/status")
    print(f"   🔄 Reset injection:    http://localhost:{port}/inject/reset")
    print(f"   📝 API endpoints:      /api/users, /api/products, /api/orders, /api/slow, /api/error")
    print(f"   Press Ctrl+C to stop")
    server.serve_forever()

if __name__ == '__main__':
    run_server(PORT)
