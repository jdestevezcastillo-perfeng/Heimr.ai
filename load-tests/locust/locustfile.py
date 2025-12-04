# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
"""
Locust load test for Heimr test application
"""
from locust import HttpUser, task, between
import random
import json

class TestAppUser(HttpUser):
    """User that interacts with the test application."""
    
    wait_time = between(0.5, 2)
    
    @task(4)
    def list_users(self):
        """List users - fast indexed query (weight: 4)."""
        with self.client.get("/api/users?limit=10", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(2)
    def query_audit_logs(self):
        """Query audit logs - SLOW unindexed query (weight: 2)."""
        with self.client.get("/api/audit-logs?limit=50", catch_response=True, name="/api/audit-logs") as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(2)
    def create_user(self):
        """Create a new user (weight: 2)."""
        payload = {
            "username": f"locust_user_{random.randint(1, 100000)}",
            "email": f"locust_{random.randint(1, 100000)}@example.com"
        }
        with self.client.post("/api/users", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(1)
    def health_check(self):
        """Health check (weight: 1)."""
        self.client.get("/health")
    
    @task(1)
    def count_audit_logs(self):
        """Count audit logs (weight: 1)."""
        with self.client.get("/api/audit-logs/count", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "count" in data:
                    response.success()
                else:
                    response.failure("Missing count field")
            else:
                response.failure(f"Status: {response.status_code}")


# Run with:
# locust -f locustfile.py --host=http://localhost:30808 -u 10 -r 2 -t 5m --csv=load-tests/results/locust
