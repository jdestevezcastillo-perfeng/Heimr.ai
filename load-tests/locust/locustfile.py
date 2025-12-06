# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

"""
Heimr Demo - Locust Load Test
Run: locust -f locustfile.py --headless -u 10 -r 1 --run-time 5m --csv=results/locust
"""

import random
import time
from locust import HttpUser, task, between


class DemoUser(HttpUser):
    """Simulates user behavior on the demo application."""
    
    wait_time = between(0.5, 2.5)  # Think time between requests
    
    @task(40)
    def get_users(self):
        """Fetch users list - most common action."""
        with self.client.get("/api/users", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(30)
    def get_products(self):
        """Fetch product catalog."""
        with self.client.get("/api/products", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(15)
    def create_order(self):
        """Create a new order - simulates purchase."""
        payload = {
            "userId": random.randint(1, 3),
            "productId": random.randint(1, 3),
            "quantity": random.randint(1, 5),
        }
        
        with self.client.post(
            "/api/orders",
            json=payload,
            catch_response=True
        ) as response:
            if response.status_code == 201:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(10)
    def health_check(self):
        """Basic health check."""
        self.client.get("/health")
    
    @task(5)
    def slow_endpoint(self):
        """Hit the slow endpoint - tests timeout handling."""
        with self.client.get(
            "/api/slow",
            timeout=10,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    def on_start(self):
        """Called when a simulated user starts."""
        # Initial health check to warm up
        self.client.get("/health")


class AdminUser(HttpUser):
    """Simulates admin/monitoring behavior - fewer users."""
    
    weight = 1  # 1 admin for every 10 regular users
    wait_time = between(5, 10)
    
    @task
    def check_health(self):
        """Periodic health monitoring."""
        self.client.get("/health")
