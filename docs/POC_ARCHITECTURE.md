# Heimr.ai - POC Architecture

## 🎯 Project Overview

Build an AI-powered performance analysis system that can:

1. **Detect** performance bottlenecks in LLM inference systems
2. **Diagnose** root causes of performance issues
3. **Recommend** optimization strategies

---

## 🏗️ POC Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                    PERFORMANCE ANALYZER AI POC                   │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│  1. DATA         │      │  2. DATA         │      │  3. MODEL        │
│  GENERATION      │─────▶│  STORAGE         │─────▶│  TRAINING        │
└──────────────────┘      └──────────────────┘      └──────────────────┘
                                                              │
                                                              ▼
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│  6. PRODUCTION   │◀─────│  5. EVALUATION   │◀─────│  4. INFERENCE    │
│  DEPLOYMENT      │      │  & VALIDATION    │      │  ENGINE          │
└──────────────────┘      └──────────────────┘      └──────────────────┘
```

---

## 📦 Component Breakdown

### 1. Data Generation (✅ COMPLETE)

**Status**: Working chaos generator with 10 failure scenarios

**Components**:

- `error-generator/` - FastAPI service with chaos injection
- **Observability Stack**:
  - Prometheus (Metrics)
  - Loki (Logs)
  - Tempo (Traces)
  - NVIDIA GPU Exporter (GPU Metrics)
- Grafana visualization
- k6 load testing scripts

**Output**:

- Time-series metrics (Prometheus format)
- Request/response logs
- Labeled chaos scenarios

---

### 2. Data Storage (🚧 IN PROGRESS)

**Purpose**: Store and organize training data

**Components**:

```text
data-pipeline/
├── collectors/
│   ├── prometheus_exporter.py    # Export Prometheus metrics
│   ├── log_collector.py           # Collect application logs
│   └── metrics_aggregator.py      # Aggregate time-series data
│
├── storage/
│   ├── parquet_writer.py          # Write to Parquet format
│   ├── dataset_builder.py         # Build training datasets
│   └── schema.py                  # Data schema definitions
│
└── datasets/
    ├── raw/                       # Raw Prometheus/logs
    ├── processed/                 # Cleaned & labeled data
    └── training/                  # Train/val/test splits
```

**Data Schema**:

```python
{
    "timestamp": datetime,
    "scenario": str,              # "latency_spike", "error_spike", etc.
    "metrics": {
        "request_rate": float,
        "p50_latency": float,
        "p95_latency": float,
        "p99_latency": float,
        "error_rate": float,
        "cpu_usage": float,
        "memory_usage": float,
        "gpu_utilization": float
    },
    "labels": {
        "has_bottleneck": bool,
        "bottleneck_type": str,   # "latency", "errors", "resources"
        "severity": str,           # "low", "medium", "high", "critical"
        "root_cause": str          # Human-readable explanation
    }
}
```

**Storage Format**: Apache Parquet (efficient for ML workloads)

---

### 3. Model Training (🔨 TO BUILD)

**Purpose**: Train AI model to detect and diagnose performance issues

**Model Selection Options**:

#### Option A: Fine-tuned LLM (Recommended for POC)

- **Base Model**: Llama-3.1-8B or Mistral-7B
- **Training Method**: LoRA/QLoRA fine-tuning
- **Task**: Multi-task learning
  - Classification: Detect bottleneck type
  - Regression: Predict severity score
  - Generation: Explain root cause + recommendations

**Pros**:

- Leverages your existing LLM infrastructure
- Can generate natural language explanations
- Transfer learning from pre-trained knowledge

**Cons**:

- Requires more compute for training
- Larger model size

#### Option B: Specialized ML Model

- **Architecture**: Gradient Boosting (XGBoost/LightGBM) + Small LLM
- **Detection Model**: XGBoost for bottleneck classification
- **Explanation Model**: Small fine-tuned LLM (1-3B params)

**Pros**:

- Faster training and inference
- Better interpretability for metrics
- Lower resource requirements

**Cons**:

- Two-stage pipeline complexity
- Less flexible for new scenarios

#### Option C: Hybrid Approach (RECOMMENDED)

```text
┌─────────────────────────────────────────────────────────┐
│  Stage 1: Detection (XGBoost)                           │
│  - Input: Time-series metrics                           │
│  - Output: Bottleneck type + confidence                 │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Stage 2: Diagnosis (Fine-tuned LLM)                    │
│  - Input: Metrics + detected bottleneck                 │
│  - Output: Root cause explanation + recommendations     │
└─────────────────────────────────────────────────────────┘
```

**Why Hybrid?**:

- Fast, accurate detection with XGBoost
- Rich explanations from LLM
- Best of both worlds for POC

---

### 4. Inference Engine (🔨 TO BUILD)

**Purpose**: Real-time performance analysis

**Components**:

```text
inference-engine/
├── api/
│   ├── main.py                    # FastAPI service
│   ├── models.py                  # Pydantic schemas
│   └── routes/
│       ├── analyze.py             # POST /analyze endpoint
│       └── health.py              # Health checks
│
├── detectors/
│   ├── bottleneck_detector.py     # XGBoost inference
│   └── feature_extractor.py       # Extract features from metrics
│
├── explainers/
│   ├── llm_explainer.py           # LLM-based explanations
│   └── prompt_templates.py        # Prompt engineering
│
└── models/
    ├── detector.pkl               # Trained XGBoost model
    └── explainer/                 # Fine-tuned LLM weights
```

**API Example**:

```python
POST /analyze
{
    "metrics": {
        "p50_latency": 45.2,
        "p95_latency": 120.5,
        "p99_latency": 3500.0,  # ⚠️ Spike!
        "error_rate": 0.02,
        "request_rate": 150
    },
    "time_window": "5m"
}

Response:
{
    "bottleneck_detected": true,
    "bottleneck_type": "latency_spike",
    "confidence": 0.94,
    "severity": "high",
    "explanation": "Detected p99 latency spike (3.5s vs baseline 120ms). 
                    This indicates tail latency issues affecting 1% of requests.
                    Likely causes: GC pauses, network congestion, or cache misses.",
    "recommendations": [
        "Check GC logs for long pause times",
        "Review network latency to upstream services",
        "Analyze cache hit rates for degradation"
    ]
}
```

---

### 5. Evaluation & Validation (🚧 IN PROGRESS)

**Purpose**: Measure model performance and benchmark inference engines

**Components**:

- **Benchmarking Suite**:
  - Automated scripts (`run_4_stage_benchmark.sh`)
  - Comparison of vLLM vs TGI
  - Performance metrics (Latency, Throughput, GPU Utilization)
- **Model Evaluation**:
  - Detection Accuracy: Precision, Recall, F1-score
  - Severity Prediction: MAE, RMSE
  - Explanation Quality: Human evaluation + BLEU/ROUGE scores

**Test Scenarios**:

- Known chaos scenarios (ground truth)
- Real-world performance data (if available)
- Edge cases and adversarial examples

---

### 6. Production Deployment (🔨 TO BUILD)

**Purpose**: Deploy as a monitoring service

**Architecture**:

```text
┌──────────────┐
│  Prometheus  │──┐
└──────────────┘  │
                  ├──▶ ┌─────────────────────┐
┌──────────────┐  │    │  Inference Engine   │
│  vLLM/TGI    │──┤    │  (FastAPI)          │
└──────────────┘  │    └─────────────────────┘
                  │              │
┌──────────────┐  │              ▼
│  Grafana     │──┘    ┌─────────────────────┐
└──────────────┘       │  Alerts & Reports   │
                       └─────────────────────┘
```

---

## 🗂️ Proposed Directory Structure

```text
Performange-analyzer-AI/
├── error-generator/              # ✅ Existing
│   └── (current chaos generator)
│
├── data-pipeline/                # 🔨 NEW
│   ├── collectors/
│   ├── storage/
│   ├── datasets/
│   └── README.md
│
├── model-training/               # 🔨 NEW
│   ├── notebooks/                # Exploratory analysis
│   ├── scripts/
│   │   ├── train_detector.py     # Train XGBoost
│   │   ├── train_explainer.py    # Fine-tune LLM
│   │   └── evaluate.py           # Model evaluation
│   ├── configs/
│   │   ├── detector_config.yaml
│   │   └── explainer_config.yaml
│   └── models/                   # Saved model artifacts
│
├── inference-engine/             # 🔨 NEW
│   ├── api/
│   ├── detectors/
│   ├── explainers/
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── evaluation/                   # 🔨 NEW
│   ├── benchmarks/
│   ├── test_cases/
│   └── reports/
│
└── docs/
    ├── POC_ARCHITECTURE.md       # This file
    ├── DATA_SCHEMA.md
    ├── MODEL_SELECTION.md
    └── DEPLOYMENT_GUIDE.md
```

---

## 🚀 Implementation Roadmap

### Phase 1: Data Pipeline (Week 1)

- [ ] Build Prometheus metrics exporter
- [ ] Create Parquet dataset builder
- [ ] Define data schema
- [ ] Generate initial training dataset (1000+ examples)

### Phase 2: Model Training (Week 2)

- [ ] Train XGBoost bottleneck detector
- [ ] Fine-tune LLM for explanations (LoRA)
- [ ] Evaluate model performance
- [ ] Iterate on feature engineering

### Phase 3: Inference Engine (Week 3)

- [ ] Build FastAPI inference service
- [ ] Integrate trained models
- [ ] Create API endpoints
- [ ] Add monitoring and logging

### Phase 4: Integration & Testing (Week 4)

- [ ] Connect to live chaos generator
- [ ] End-to-end testing
- [ ] Performance benchmarking
- [ ] Documentation

---

## 💡 Key Decisions Needed

### 1. Model Selection

**Question**: Which approach do you prefer?

- **A**: Fine-tuned LLM only (simpler, but slower)
- **B**: XGBoost + Small LLM (faster, more complex)
- **C**: Hybrid (recommended)

### 2. Training Infrastructure

**Question**: What GPU resources do you have?

- Current: NVIDIA 3090 (24GB VRAM)
- Sufficient for: LoRA fine-tuning of 8B models
- May need: Quantization (4-bit) for larger models

### 3. Dataset Size

**Question**: How much training data should we generate?

- **Minimum POC**: 1,000 examples (100 per scenario)
- **Better POC**: 10,000 examples (1,000 per scenario)
- **Production**: 100,000+ examples

### 4. Evaluation Criteria

**Question**: What defines success for the POC?

- Detection accuracy > 90%?
- Explanation quality (human-rated)?
- Inference latency < 1 second?

---

## 📊 Success Metrics

### POC Success Criteria

1. ✅ **Data Generation**: 1,000+ labeled examples
2. ✅ **Model Training**: >85% detection accuracy
3. ✅ **Inference Speed**: <2 seconds per analysis
4. ✅ **Explanation Quality**: Actionable insights (human-validated)
5. ✅ **Integration**: Works with live chaos generator

---

## 🔗 Next Steps

1. **Review this architecture** - Does it align with your vision?
2. **Make key decisions** - Model selection, dataset size, success criteria
3. **Start Phase 1** - Build data pipeline
4. **Generate training data** - Run chaos generator extensively
5. **Train initial model** - Start with simple baseline

---

## 📝 Notes

- **POC Timeline**: 4 weeks (aggressive but achievable)
- **Tech Stack**: Python, FastAPI, XGBoost, Transformers, Parquet
- **Infrastructure**: Docker, Prometheus, Grafana (already set up)
- **GPU Requirements**: 1x NVIDIA 3090 (sufficient for POC)

---

**Ready to build?** Let's start with Phase 1: Data Pipeline! 🚀
