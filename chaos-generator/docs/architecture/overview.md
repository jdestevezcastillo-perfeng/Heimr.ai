# Heimr.ai Detailed Architecture

This document provides a comprehensive technical view of the Heimr.ai infrastructure, including Kubernetes resources, network configurations, and data flows.

![Detailed Architecture Diagram](images/detailed_architecture_1764547140313.png)

```mermaid
graph TB
    %% Styles
    classDef k8s fill:#326ce5,stroke:#fff,stroke-width:2px,color:#fff;
    classDef ns fill:#e1f5fe,stroke:#0277bd,stroke-width:2px,stroke-dasharray: 5 5;
    classDef pod fill:#fff,stroke:#326ce5,stroke-width:1px;
    classDef svc fill:#ffecb3,stroke:#ff6f00,stroke-width:1px;
    classDef vol fill:#f1f8e9,stroke:#558b2f,stroke-width:1px;
    classDef ext fill:#eceff1,stroke:#455a64,stroke-width:2px;

    subgraph "GCP Region: asia-northeast1 (Artifacts) / us-central1 (Cluster)"
        
        subgraph "GKE Cluster: heimr-cluster"
            direction TB
            
            subgraph "Node Pool: default-pool (3x e2-standard-4)"
                
                subgraph "Namespace: sim-api-0 (Repeated 0-11)"
                    direction TB
                    
                    %% Services Layer
                    subgraph "K8s Services (ClusterIP)"
                        SvcObs[("svc/observability\nPorts: 9090, 3100, 3200, 4317")]:::svc
                        SvcSim[("svc/sim-service\nPort: 8000")]:::svc
                        SvcDB[("svc/sim-db\nPort: 8000")]:::svc
                        SvcCache[("svc/sim-cache\nPort: 8000")]:::svc
                        SvcQueue[("svc/sim-queue\nPort: 8000")]:::svc
                        SvcInf[("svc/sim-inference\nPort: 8000")]:::svc
                        SvcChaos[("svc/chaos-controller\nPort: 8000")]:::svc
                    end

                    %% Workloads Layer
                    subgraph "Workloads (Deployments & Pods)"
                        
                        subgraph "Pod: observability-stack"
                            Prom[("Prometheus\n:9090")]:::pod
                            Loki[("Loki\n:3100")]:::pod
                            Tempo[("Tempo\n:3200")]:::pod
                            Promtail[("Promtail")]:::pod
                            
                            %% Volumes
                            VolLog[("Vol: /var/log\n(hostPath)")]:::vol
                            VolData[("Vol: emptyDir\n(Data Storage)")]:::vol
                            
                            Promtail -.-> VolLog
                            Prom -.-> VolData
                            Loki -.-> VolData
                            Tempo -.-> VolData
                        end

                        subgraph "Deployment: sim-service-agent"
                            PodSim[("sim-service\n:8000")]:::pod
                            EnvSim["Env: OTEL_EXPORTER_OTLP_ENDPOINT\nEnv: OTEL_SERVICE_NAME"]:::vol
                            PodSim -.-> EnvSim
                        end

                        subgraph "Backend Simulators"
                            PodDB[("sim-db\n:8000")]:::pod
                            PodCache[("sim-cache\n:8000")]:::pod
                            PodQueue[("sim-queue\n:8000")]:::pod
                            PodInf[("sim-inference\n:8000")]:::pod
                        end

                        subgraph "Chaos Engine"
                            PodChaos[("chaos-controller\n:8000")]:::pod
                            SAChaos[("SA: chaos-controller-sa")]:::vol
                            PodChaos -.-> SAChaos
                        end
                    end

                    %% Internal Wiring
                    SvcObs --> Prom & Loki & Tempo
                    SvcSim --> PodSim
                    SvcDB --> PodDB
                    SvcCache --> PodCache
                    SvcQueue --> PodQueue
                    SvcInf --> PodInf
                    SvcChaos --> PodChaos

                    %% App Flows
                    PodSim -- "HTTP/8000" --> SvcDB & SvcCache & SvcQueue & SvcInf
                    
                    %% Telemetry Flows
                    Prom -- "Scrape :8000/metrics" --> SvcSim & SvcDB & SvcCache & SvcQueue & SvcInf & SvcChaos
                    PodSim -- "OTLP/gRPC :4317" --> SvcObs
                    Promtail -- "Push :3100" --> Loki
                end
            end
        end

        subgraph "External / Cloud Resources"
            GCS[("GCS Bucket\nheimr-data-tokyo-snow...")]:::ext
            AR[("Artifact Registry\nheimr")]:::ext
        end
    end

    subgraph "Operator / Local Machine"
        UserScript["run_gke_generation.py"]:::ext
        K8sProxy["kubectl port-forward"]:::ext
        
        %% Data Collection Flow
        UserScript -- "1. Trigger Fault" --> K8sProxy
        UserScript -- "2. Query Metrics/Logs/Traces" --> K8sProxy
        UserScript -- "3. Upload Parquet" --> GCS
        
        K8sProxy -- ":8000" --> SvcChaos
        K8sProxy -- ":9090, :3100, :3200" --> SvcObs
    end

```

## Network Configuration Details

| Service Name | Type | Ports | Target | Description |
| :--- | :--- | :--- | :--- | :--- |
| `observability` | ClusterIP | `9090` (Prometheus)<br>`3100` (Loki)<br>`3200` (Tempo)<br>`4317` (OTLP gRPC) | `observability-stack` Pod | Central monitoring entry point. |
| `sim-service` | ClusterIP | `8000` (HTTP) | `sim-service-agent` | Main entry point for simulator topology. |
| `sim-db` | ClusterIP | `8000` (HTTP) | `sim-db` | Simulated Database backend. |
| `sim-cache` | ClusterIP | `8000` (HTTP) | `sim-cache` | Simulated Cache backend. |
| `sim-queue` | ClusterIP | `8000` (HTTP) | `sim-queue` | Simulated Message Queue. |
| `sim-inference` | ClusterIP | `8000` (HTTP) | `sim-inference` | Simulated LLM Inference Engine. |
| `chaos-controller` | ClusterIP | `8000` (HTTP) | `chaos-controller` | Fault injection controller. |

## Volume & Storage Configuration

*   **Logs**: `observability-stack` mounts `/var/log` from the host node (via `hostPath`) to allow Promtail to scrape container logs from all pods on that node.
*   **Data Persistence**: Currently using `emptyDir` for Prometheus, Loki, and Tempo storage. Data is ephemeral and lost on Pod restart.
*   **Secrets**: GCS credentials (if used by in-cluster generator) are mounted as Secrets.

## Telemetry Flow

1.  **Metrics**: Prometheus pulls metrics from all services via standard `/metrics` endpoint on port `8000`.
2.  **Logs**: Promtail (DaemonSet-style behavior, though running as sidecar here) reads node logs and pushes to Loki on `localhost:3100`.
3.  **Traces**: `sim-service-agent` is instrumented with OpenTelemetry. It pushes traces to `http://observability:4317` (which routes to Tempo).
