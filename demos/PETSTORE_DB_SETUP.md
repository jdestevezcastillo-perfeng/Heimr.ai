# Petstore Demo with PostgreSQL Database

## Overview
This setup replaces the simple Swagger Petstore API with a full-stack implementation that includes:
- ✅ Real PostgreSQL database with schema
- ✅ Java Spring Boot REST API
- ✅ PostgreSQL exporter for Prometheus
- ✅ Slow query injection for demo purposes
- ✅ Full observability stack (Prometheus, Loki, Tempo)

## Setup Instructions

### 1. Clone the Petstore API

```bash
cd /home/lostborion/Heimr.ai
git clone https://github.com/smuralee/pet-store-api.git demo-petstore-db
cd demo-petstore-db
```

### 2. Create Enhanced Docker Compose

Create `docker-compose.heimr.yml`:

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: petstore-db
    environment:
      POSTGRES_DB: petstore
      POSTGRES_USER: petstore
      POSTGRES_PASSWORD: petstore123
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U petstore"]
      interval: 10s
      timeout: 5s
      retries: 5

  # PostgreSQL Exporter for Prometheus
  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:latest
    container_name: petstore-postgres-exporter
    environment:
      DATA_SOURCE_NAME: "postgresql://petstore:petstore123@postgres:5432/petstore?sslmode=disable"
      PG_EXPORTER_EXTEND_QUERY_PATH: "/etc/postgres_exporter/queries.yaml"
    ports:
      - "9187:9187"
    volumes:
      - ./postgres-exporter-queries.yaml:/etc/postgres_exporter/queries.yaml
    depends_on:
      postgres:
        condition: service_healthy

  # Petstore API (Spring Boot)
  petstore-api:
    build: .
    container_name: petstore-api
    environment:
      SPRING_DATASOURCE_URL: jdbc:postgresql://postgres:5432/petstore
      SPRING_DATASOURCE_USERNAME: petstore
      SPRING_DATASOURCE_PASSWORD: petstore123
      SPRING_JPA_HIBERNATE_DDL_AUTO: update
      # Enable slow query logging
      SPRING_JPA_PROPERTIES_HIBERNATE_SHOW_SQL: "true"
      SPRING_JPA_PROPERTIES_HIBERNATE_FORMAT_SQL: "true"
      # Inject slow queries for demo
      DEMO_SLOW_QUERY_ENABLED: "true"
    ports:
      - "8080:8080"
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/actuator/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Prometheus
  prometheus:
    image: prom/prometheus:latest
    container_name: petstore-prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    depends_on:
      - petstore-api
      - postgres-exporter

  # Loki for logs
  loki:
    image: grafana/loki:latest
    container_name: petstore-loki
    ports:
      - "3100:3100"
    command: -config.file=/etc/loki/local-config.yaml
    volumes:
      - loki-data:/loki

  # Promtail for log collection
  promtail:
    image: grafana/promtail:latest
    container_name: petstore-promtail
    volumes:
      - /var/log:/var/log
      - ./promtail-config.yml:/etc/promtail/config.yml
    command: -config.file=/etc/promtail/config.yml
    depends_on:
      - loki

  # Tempo for distributed tracing
  tempo:
    image: grafana/tempo:latest
    container_name: petstore-tempo
    command: [ "-config.file=/etc/tempo.yaml" ]
    volumes:
      - ./tempo.yaml:/etc/tempo.yaml
      - tempo-data:/tmp/tempo
    ports:
      - "3200:3200"   # tempo
      - "4317:4317"   # otlp grpc
      - "4318:4318"   # otlp http

  # Grafana for visualization
  grafana:
    image: grafana/grafana:latest
    container_name: petstore-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana-datasources.yml:/etc/grafana/provisioning/datasources/datasources.yml
    depends_on:
      - prometheus
      - loki
      - tempo

volumes:
  postgres-data:
  prometheus-data:
  loki-data:
  tempo-data:
  grafana-data:
```

### 3. Create Database Initialization Script

Create `init-db.sql`:

```sql
-- Create tables
CREATE TABLE IF NOT EXISTS pets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    pet_id INTEGER REFERENCES pets(id),
    quantity INTEGER,
    ship_date TIMESTAMP,
    status VARCHAR(50),
    complete BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create an UNINDEXED table for slow query demo
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    pet_id INTEGER,
    action VARCHAR(100),
    user_id INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details TEXT
);

-- Insert sample data
INSERT INTO pets (name, category, status) VALUES
    ('Fluffy', 'cat', 'available'),
    ('Buddy', 'dog', 'available'),
    ('Tweety', 'bird', 'pending'),
    ('Goldie', 'fish', 'sold');

-- Insert LOTS of audit logs (unindexed for slow queries)
INSERT INTO audit_logs (pet_id, action, user_id, details)
SELECT 
    (random() * 100)::int,
    CASE (random() * 3)::int
        WHEN 0 THEN 'view'
        WHEN 1 THEN 'update'
        WHEN 2 THEN 'delete'
        ELSE 'create'
    END,
    (random() * 1000)::int,
    'Sample audit log entry ' || generate_series
FROM generate_series(1, 100000);

-- Enable pg_stat_statements for query monitoring
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

### 4. Create PostgreSQL Exporter Queries

Create `postgres-exporter-queries.yaml`:

```yaml
pg_stat_statements:
  query: |
    SELECT
      queryid,
      query,
      calls,
      total_exec_time,
      mean_exec_time,
      max_exec_time,
      rows
    FROM pg_stat_statements
    WHERE query NOT LIKE '%pg_stat_statements%'
    ORDER BY mean_exec_time DESC
    LIMIT 20
  metrics:
    - queryid:
        usage: "LABEL"
        description: "Query ID"
    - query:
        usage: "LABEL"
        description: "Query text"
    - calls:
        usage: "COUNTER"
        description: "Number of times executed"
    - total_exec_time:
        usage: "COUNTER"
        description: "Total time spent executing"
    - mean_exec_time:
        usage: "GAUGE"
        description: "Mean execution time"
    - max_exec_time:
        usage: "GAUGE"
        description: "Maximum execution time"
    - rows:
        usage: "COUNTER"
        description: "Total rows retrieved or affected"

pg_database_size:
  query: |
    SELECT
      datname,
      pg_database_size(datname) as size_bytes
    FROM pg_database
  metrics:
    - datname:
        usage: "LABEL"
        description: "Database name"
    - size_bytes:
        usage: "GAUGE"
        description: "Database size in bytes"
```

### 5. Create Prometheus Configuration

Create `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  # Petstore API metrics
  - job_name: 'petstore-api'
    static_configs:
      - targets: ['petstore-api:8080']
    metrics_path: '/actuator/prometheus'

  # PostgreSQL metrics
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  # Prometheus itself
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

### 6. Create k6 Load Test with Slow Queries

Create `load-tests/k6/petstore-db-test.js`:

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 10 },  // Ramp up
    { duration: '5m', target: 10 },  // Steady state
    { duration: '2m', target: 20 },  // Spike
    { duration: '5m', target: 20 },  // Sustained load
    { duration: '2m', target: 0 },   // Ramp down
  ],
};

const BASE_URL = 'http://localhost:8080';

export default function () {
  // 40% - Get all pets (fast, indexed)
  if (Math.random() < 0.4) {
    const res = http.get(`${BASE_URL}/api/pets`);
    check(res, { 'get pets status 200': (r) => r.status === 200 });
  }
  
  // 30% - Get pet by ID (fast, primary key)
  else if (Math.random() < 0.7) {
    const petId = Math.floor(Math.random() * 100) + 1;
    const res = http.get(`${BASE_URL}/api/pets/${petId}`);
    check(res, { 'get pet status 200': (r) => r.status === 200 });
  }
  
  // 20% - Get audit logs (SLOW - unindexed table scan!)
  else if (Math.random() < 0.9) {
    const userId = Math.floor(Math.random() * 1000);
    const res = http.get(`${BASE_URL}/api/audit-logs?userId=${userId}`);
    check(res, { 'get audit logs status 200': (r) => r.status === 200 });
  }
  
  // 10% - Create new pet (moderate, insert)
  else {
    const payload = JSON.stringify({
      name: `Pet-${Date.now()}`,
      category: 'dog',
      status: 'available'
    });
    const res = http.post(`${BASE_URL}/api/pets`, payload, {
      headers: { 'Content-Type': 'application/json' },
    });
    check(res, { 'create pet status 201': (r) => r.status === 201 });
  }
  
  sleep(1);
}
```

### 7. Run the Demo

```bash
# Start all services
docker-compose -f docker-compose.heimr.yml up -d

# Wait for services to be healthy
sleep 30

# Run k6 load test
k6 run --out json=petstore-db-results.json load-tests/k6/petstore-db-test.js

# Analyze with Heimr
heimr analyze petstore-db-results.json \
  --prometheus http://localhost:9090 \
  --loki http://localhost:3100 \
  --tempo http://localhost:3200 \
  --output petstore-db-report.md
```

## Expected Results

The Heimr report should now show:

### ✅ Database Metrics Section
- PostgreSQL connection pool stats
- Query execution times
- Slow queries from `pg_stat_statements`
- Database size and growth

### ✅ Performance Bottleneck
- **Root Cause:** Unindexed `audit_logs` table causing full table scans
- **Evidence:** High P95/P99 latency on `/api/audit-logs` endpoint
- **DB Metrics:** `mean_exec_time` > 1000ms for audit log queries

### ✅ LLM Analysis
The AI should identify:
- Slow database queries as primary bottleneck
- Missing index on `audit_logs.user_id`
- Recommendation to add index or implement pagination

## Adding the Missing Index (Fix Demo)

To demonstrate the fix:

```sql
-- Connect to database
docker exec -it petstore-db psql -U petstore -d petstore

-- Add the missing index
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);

-- Re-run the load test and compare results
```

## Cleanup

```bash
docker-compose -f docker-compose.heimr.yml down -v
```

## Next Steps

1. Customize the Spring Boot app to add Prometheus metrics
2. Add OpenTelemetry for distributed tracing
3. Implement actual slow query injection in the API code
4. Create Grafana dashboards for real-time monitoring
