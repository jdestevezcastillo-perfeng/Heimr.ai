# Heimr.ai

> AI-powered performance analysis system that detects bottlenecks in LLM inference systems, diagnoses root causes, and recommends optimization strategies.

---

## 🎯 Project Overview

This project trains an AI model to analyze performance metrics from LLM inference engines (vLLM, TGI) and automatically:
- **Detect** performance bottlenecks (latency spikes, errors, resource constraints)
- **Diagnose** root causes with natural language explanations
- **Recommend** actionable optimization strategies

---

## 🏗️ Architecture

```
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│  Chaos Generator │─────▶│  Data Pipeline   │─────▶│  Model Training  │
│  (Training Data) │      │  (Parquet)       │      │  (XGBoost + LLM) │
└──────────────────┘      └──────────────────┘      └──────────────────┘
                                                              │
                                                              ▼
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│  Production      │◀─────│  Evaluation      │◀─────│  Inference API   │
│  Deployment      │      │  & Validation    │      │  (FastAPI)       │
└──────────────────┘      └──────────────────┘      └──────────────────┘
```

---

## 📂 Project Structure

```
Performange-analyzer-AI/
├── ratatoskr/          # ✅ Training data generation
│   ├── app/                  # FastAPI chaos injection service
│   ├── grafana/              # Visualization dashboards
│   ├── k6/                   # Load testing scripts
│   └── docker-compose.yml    # Full stack deployment
│
├── data-pipeline/            # 🔨 Data collection & storage
│   ├── collectors/           # Prometheus exporters
│   ├── storage/              # Parquet dataset builders
│   └── datasets/             # Training data
│
├── model-training/           # 🔨 ML model training
│   ├── scripts/              # Training scripts
│   │   ├── train_detector.py     # XGBoost classifier
│   │   └── train_explainer.py    # LLM fine-tuning
│   └── models/               # Saved model artifacts
│
├── inference-engine/         # 🔨 Real-time analysis API
│   ├── api/                  # FastAPI service
│   ├── detectors/            # Bottleneck detection
│   └── explainers/           # LLM-based explanations
│
└── docs/
    ├── POC_ARCHITECTURE.md   # Full architecture design
    └── IMPLEMENTATION_PLAN.md # Detailed implementation plan
```

**Legend**: ✅ Complete | 🔨 In Progress | ⏳ Planned

---

## 🚀 Quick Start

### 1. Chaos Generator (Training Data)

Generate labeled performance data with controlled failure scenarios:

```bash
cd ratatoskr
docker-compose up -d

# Access services
# - Chaos API: http://localhost:8000
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000
```

**Available Chaos Scenarios**:
- Healthy baseline
- Latency spikes (p99 anomalies)
- Error spikes (5xx errors)
- Bimodal latency (cache hit/miss)
- Gradual degradation
- Rate limiting (429 errors)
- CPU-bound operations
- Memory leaks
- Intermittent errors
- Cascading failures

See [`ratatoskr/README.md`](ratatoskr/README.md) for details.

---

### 2. Data Pipeline (Coming Soon)

Export Prometheus metrics and build training datasets:

```bash
cd data-pipeline
python scripts/generate_training_data.py
```

---

### 3. Model Training (Coming Soon)

Train the hybrid AI model:

```bash
cd model-training

# Train bottleneck detector (XGBoost)
python scripts/train_detector.py

# Fine-tune explanation generator (LLM)
python scripts/train_explainer.py
```

---

### 4. Inference Engine (Coming Soon)

Deploy the analysis API:

```bash
cd inference-engine
docker-compose up -d

# Analyze metrics
curl -X POST http://localhost:8080/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "metrics": {
      "p50_latency": 45.2,
      "p95_latency": 120.5,
      "p99_latency": 3500.0,
      "error_rate": 0.02
    }
  }'
```

---

## 📊 Model Architecture

### Hybrid Approach (Recommended)

```
┌─────────────────────────────────────────────────────────┐
│  Stage 1: Bottleneck Detection (XGBoost)                │
│  - Input: Time-series metrics (p50, p95, p99, errors)   │
│  - Output: Bottleneck type + confidence score           │
│  - Inference: <10ms                                     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Stage 2: Root Cause Explanation (Fine-tuned LLM)       │
│  - Base Model: Llama-3.1-8B or Mistral-7B              │
│  - Training: LoRA/QLoRA fine-tuning                     │
│  - Output: Natural language explanation + fixes        │
│  - Inference: <2 seconds                                │
└─────────────────────────────────────────────────────────┘
```

**Why Hybrid?**
- **Fast detection** with XGBoost (10ms)
- **Rich explanations** from fine-tuned LLM
- **Best accuracy** for POC demonstration

---

## 📈 Training Data Schema

```python
{
    "timestamp": datetime,
    "scenario": str,              # Ground truth label
    "metrics": {
        "request_rate": float,
        "p50_latency": float,
        "p95_latency": float,
        "p99_latency": float,
        "error_rate": float,
        "cpu_usage": float,
        "memory_usage": float
    },
    "labels": {
        "has_bottleneck": bool,
        "bottleneck_type": str,   # "latency", "errors", "resources"
        "severity": str,           # "low", "medium", "high", "critical"
        "root_cause": str,         # Human-readable explanation
        "recommendations": list[str]
    }
}
```

---

## 🎯 POC Success Criteria

- [x] **Data Generation**: Chaos generator with 10 scenarios
- [ ] **Dataset**: 1,000+ labeled training examples
- [ ] **Detection Accuracy**: >85% on test set
- [ ] **Inference Speed**: <2 seconds per analysis
- [ ] **Explanation Quality**: Human-validated actionable insights
- [ ] **Integration**: Works with live Prometheus metrics

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Data Generation** | FastAPI, Prometheus, Grafana, k6 |
| **Data Storage** | Apache Parquet, Pandas |
| **Detection Model** | XGBoost, scikit-learn |
| **Explanation Model** | Llama-3.1-8B, Transformers, LoRA |
| **Inference API** | FastAPI, Uvicorn |
| **Infrastructure** | Docker, Docker Compose |
| **GPU** | NVIDIA 3090 (24GB VRAM) |

---

## 📚 Documentation

- **[POC Architecture](docs/POC_ARCHITECTURE.md)** - Complete system design
- **[Implementation Plan](IMPLEMENTATION_PLAN.md)** - Detailed roadmap
- **[Chaos Generator](ratatoskr/README.md)** - Training data generation
- **[Data Pipeline](data-pipeline/README.md)** - Data collection & storage
- **[Model Training](model-training/README.md)** - ML model details
- **[Website Preview](website/heimr-homepage.html)** - Heimr.ai homepage

---

## 🗓️ Roadmap

| Phase | Status | Timeline |
|-------|--------|----------|
| **Phase 0**: Chaos Generator | ✅ Complete | Week 0 |
| **Phase 1**: Data Pipeline | ✅ Complete | Week 1 |
| **Phase 2**: Model Training | ✅ Complete | Week 2 |
| **Phase 3**: Inference Engine | ⏳ Planned | Week 3 |
| **Phase 4**: Integration & Testing | ⏳ Planned | Week 4 |

---

## 🤝 Contributing

This is a learning project focused on AI performance engineering. Key areas:
- LLM inference optimization (vLLM, TGI)
- Performance metrics analysis
- ML model training and fine-tuning
- Real-time anomaly detection

---

## 📝 License

MIT License - See LICENSE file for details

---

## 🔗 Related Projects

- [vLLM](https://github.com/vllm-project/vllm) - High-throughput LLM inference
- [Text Generation Inference](https://github.com/huggingface/text-generation-inference) - HuggingFace TGI
- [Prometheus](https://prometheus.io/) - Metrics collection
- [Grafana](https://grafana.com/) - Visualization

---

**Status**: 🔨 Active Development | **POC Target**: 4 weeks | **Current Phase**: Data Pipeline

Built with ❤️ for AI Performance Engineering
