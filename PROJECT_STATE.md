---
project_name: "Heimr.ai"
last_updated: "2025-12-01T04:05:00+01:00"
# AGENT INSTRUCTION: ALWAYS UPDATE THIS FILE WHEN MAKING SIGNIFICANT CHANGES (INFRA, DEPLOYMENT, VALIDATION).
# THIS FILE IS THE SOURCE OF TRUTH FOR PROJECT STATE.
infrastructure:
  gcp_project_id: "tokyo-snow-479722-a2"
  region: "asia-northeast1"
  zone: "us-central1-a"
  authentication:
    type: "Service Account Key"
    service_account: "heimr-agent-sa@tokyo-snow-479722-a2.iam.gserviceaccount.com"
    key_path: "/home/lostborion/.gcp/heimr-agent-sa.json"
    env_var: "GOOGLE_APPLICATION_CREDENTIALS"
  gke_cluster:
    name: "heimr-cluster"
    node_count: 3
    machine_type: "e2-standard-4"
    status: "ACTIVE"
  artifact_registry:
    name: "heimr"
    location: "us-central1"
  gcs_bucket:
    name: "heimr-data-tokyo-snow-479722-a2"
    location: "US-CENTRAL1"
deployment:
  namespaces:
    pattern: "sim-api-{0..11}"
    count: 12
  workloads:
    - name: "sim-service-agent"
      image: "heimr/sim-service-agent:instrumented"
      port: 8000
    - name: "sim-db"
      image: "heimr/sim-db-agent:instrumented"
      port: 8000
    - name: "sim-cache"
      image: "heimr/sim-cache-agent:instrumented"
      port: 8000
    - name: "sim-queue"
      image: "heimr/sim-queue-agent:instrumented"
      port: 8000
    - name: "sim-inference"
      image: "heimr/sim-inference:instrumented"
      port: 8000
    - name: "chaos-controller"
      image: "heimr/chaos-controller:instrumented"
      port: 8000
  observability:
    pod_name: "observability-stack"
    components:
      - name: "prometheus"
        port: 9090
        volume: "emptyDir"
      - name: "loki"
        port: 3100
        volume: "emptyDir"
      - name: "tempo"
        port: 3200
        otlp_grpc: 4317
        volume: "emptyDir"
      - name: "promtail"
        volume: "hostPath (/var/log)"
validation_status:
  metrics:
    status: "PASS"
    details: "Verified in Parquet file. Prometheus scraping successful."
  logs:
    status: "PASS"
    details: "Verified in Parquet file (300+ logs/run). Promtail fixed with hostPath mount and privileged mode."
  traces:
    status: "PASS"
    details: "Verified in Parquet file (100+ traces/run). Traffic generator implemented to trigger traces."
known_issues:
  - id: "QUEUE_CONFUSION"
    description: "Previous diagrams labeled queue as RabbitMQ; code confirms it is Kafka."
    status: "RESOLVED"
recent_actions:
  - "Imported existing GCP infrastructure to Terraform."
  - "Refactored Terraform to match GKE state (Workload Identity, Monitoring)."
  - "Destroyed and recreated infrastructure to verify reproducibility."
  - "Deployed 12 simulator topologies."
  - "Fixed `observability-pod.yaml` (Promtail hostPath, Tempo memory)."
  - "Fixed `sim-deployments.yaml` (Added OTEL env vars)."
  - "Implemented Traffic Generator in `run_gke_generation.py`."
  - "Updated Data Pipeline to use `service.name` for trace queries and 60s lookback."
  - "Verified full observability data (Metrics, Logs, Traces) in Parquet."
  - "Moved Source of Truth files (Project State, Manifest, Schema, Config, Scenarios) to root directory."
---

# Project State Documentation

## Overview
This document serves as a machine-readable source of truth for the current state of the Heimr.ai project. It is intended to allow any AI agent to quickly context-switch into the project and understand the infrastructure, deployment, and current challenges.

## Architecture
The project consists of a GKE cluster running multiple isolated "Simulator Topologies". Each topology represents a microservices architecture (Service, DB, Cache, Queue, Inference) subject to Chaos Injection.

### Key Components
1.  **Simulator Namespace (`sim-api-X`)**:
    *   Contains the application microservices.
    *   Contains a dedicated `observability-stack` pod (Prometheus, Loki, Tempo).
    *   Contains a `chaos-controller` for fault injection.
2.  **Data Pipeline**:
    *   **Architecture**: Kubernetes Job (`k8s/base/pipeline/job-parallel.yaml`) running inside the cluster.
    *   **Orchestrator**: `run_gke_generation.py` (running in the Job).
    *   **Data Flow**: Simulators -> Observability Stack -> Data Pipeline (Job) -> GCS Bucket.
    *   **Status**: Active (Running 20 parallel workers).

## Current Status Details

### Infrastructure
*   **Terraform**: State is consistent. Infrastructure has been successfully recreated.
*   **GKE**: Running 3 nodes. Resource quotas are tight (12 vCPU limit), so workload is capped at 12 topologies.

### Observability Debugging
We have spent significant time debugging the observability pipeline:
1.  **Prometheus**: Working. Scrapes all services on port 8000.
2.  **Loki**: Working, but receiving no application logs. Promtail was fixed to mount `/var/log`, but application logs (stdout) might not be flowing as expected or the volume mount might still be tricky with the sidecar pattern.
3.  **Tempo**: Working, but receiving no traces.
    *   **Fix Applied**: Added `OTEL_EXPORTER_OTLP_ENDPOINT` to all deployments.
    *   **Remaining Issue**: The application (`sim-service-agent`) is passive. It needs incoming HTTP requests to generate traces. The current data generator only triggers chaos (config change) but does not send user traffic.

## Next Steps
1.  **Traffic Generation**: We must modify the data generation pipeline to send actual HTTP requests to `sim-service-agent` during the data collection window. This will generate the missing traces and logs.
2.  **Verify Fix**: Once traffic is flowing, re-run `run_gke_generation.py` and inspect the Parquet file again.
