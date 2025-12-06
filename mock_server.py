import http.server
import socketserver
import json
import time
import random
import threading

PORT = 30808

class MockRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Simulate network/processing latency
        time.sleep(random.uniform(0.01, 0.05)) 
        
        if self.path.startswith("/api/users"):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            data = [{"id": i, "name": f"User {i}"} for i in range(10)]
            self.wfile.write(json.dumps(data).encode())
            
        elif self.path.startswith("/api/audit-logs"):
            # Simulate slow endpoint
            time.sleep(random.uniform(0.1, 0.5))
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"logs": []}).encode())
            
        elif self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        time.sleep(random.uniform(0.05, 0.1))
        if self.path == "/api/users":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "created"}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return # Silence logs

print(f"Starting mock server on port {PORT}")
with socketserver.TCPServer(("", PORT), MockRequestHandler) as httpd:
    httpd.serve_forever()
