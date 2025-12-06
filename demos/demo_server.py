#!/usr/bin/env python3
# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.

"""
Standalone Demo API Server
Run: python3 demo_server.py
"""

import os
import time
import random
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import threading

class DemoHandler(BaseHTTPRequestHandler):
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
        path = urlparse(self.path).path
        
        # Add small random latency (10-50ms)
        time.sleep(random.uniform(0.01, 0.05))
        
        if path == '/health':
            self.send_json(200, {"status": "healthy", "timestamp": time.time()})
        
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
            self.send_json(500, {"error": "Internal Server Error", "code": "E500"})
        
        elif path == '/metrics':
            metrics = "# HELP requests_total Total requests\n# TYPE requests_total counter\nrequests_total 0\n"
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(metrics.encode())
        
        else:
            self.send_json(404, {"error": "Not Found"})
    
    def do_POST(self):
        path = urlparse(self.path).path
        
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
            self.send_json(201, {"order": order, "message": "Order created"})
        
        else:
            self.send_json(404, {"error": "Not Found"})
    
    def log_message(self, format, *args):
        pass  # Suppress request logs


def run_server(port=8080):
    server = HTTPServer(('0.0.0.0', port), DemoHandler)
    print(f"🚀 Demo API Server running on http://localhost:{port}")
    print(f"   Endpoints: /api/users, /api/products, /api/orders, /api/slow, /api/error, /health")
    print(f"   Press Ctrl+C to stop")
    server.serve_forever()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    run_server(port)
