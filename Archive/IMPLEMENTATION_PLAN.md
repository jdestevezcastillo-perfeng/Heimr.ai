# Heimr.ai - Implementation Plan

## 🎯 Current Status

✅ **Phase 0: Chaos Generator** - COMPLETE
- Working chaos generator with 10 failure scenarios
- Prometheus metrics collection
- Grafana visualization
- k6 load testing

---

## 📋 Phase 1: Data Pipeline (NEXT)

### Objectives
1. Export metrics from Prometheus
2. Structure data for ML training
3. Generate labeled training dataset
4. Store in efficient format (Parquet)

### Tasks

#### Task 1.1: Prometheus Metrics Exporter
**File**: `data-pipeline/collectors/prometheus_exporter.py`

**Functionality**:
```python
class PrometheusExporter:
    def query_range(self, metric, start, end, step):
        """Query Prometheus for time-series data"""
        
    def export_chaos_scenario(self, scenario_name, duration):
        """Export all metrics for a chaos scenario run"""
        
    def get_metrics_snapshot(self, timestamp):
        """Get point-in-time metrics snapshot"""
```

**Metrics to Export**:
- `chaos_requests_total` - Request counter
- `chaos_request_duration_seconds` - Latency histogram
- `chaos_errors_total` - Error counter by status code
- `chaos_concurrent_requests` - Active requests gauge
- `chaos_active_scenario` - Current scenario label

**Output**: JSON time-series data

---

#### Task 1.2: Dataset Builder
**File**: `data-pipeline/storage/dataset_builder.py`

**Functionality**:
```python
class DatasetBuilder:
    def create_training_example(self, metrics, scenario):
        """Convert raw metrics to training example"""
        
    def aggregate_time_window(self, metrics, window_size):
        """Aggregate metrics over time window"""
        
    def label_example(self, metrics, scenario):
        """Add ground truth labels"""
        
    def save_to_parquet(self, examples, output_path):
        """Save dataset in Parquet format"""
```

**Data Schema**:
```python
{
    "id": str,                    # Unique example ID
    "timestamp": datetime,
    "scenario": str,              # Ground truth scenario name
    "duration_seconds": int,
    
    # Aggregated metrics (5-minute window)
    "metrics": {
        "request_rate_mean": float,
        "request_rate_std": float,
        "p50_latency": float,
        "p95_latency": float,
        "p99_latency": float,
        "error_rate": float,
        "error_5xx_count": int,
        "concurrent_requests_max": int,
    },
    
    # Labels for training
    "labels": {
        "has_bottleneck": bool,
        "bottleneck_type": str,   # "latency", "errors", "rate_limit", "healthy"
        "severity": int,           # 0=none, 1=low, 2=medium, 3=high, 4=critical
        "root_cause": str,         # Human-readable explanation
        "recommendations": list[str]
    }
}
```

---

#### Task 1.3: Data Generation Script
**File**: `data-pipeline/scripts/generate_training_data.py`

**Purpose**: Automated data collection from chaos generator

**Workflow**:
```python
for scenario in CHAOS_SCENARIOS:
    for iteration in range(SAMPLES_PER_SCENARIO):
        # 1. Activate chaos scenario
        activate_scenario(scenario)
        
        # 2. Generate load (k6)
        run_load_test(duration=300)  # 5 minutes
        
        # 3. Export metrics
        metrics = export_prometheus_data()
        
        # 4. Create labeled example
        example = create_training_example(metrics, scenario)
        
        # 5. Save to dataset
        append_to_dataset(example)
        
        # 6. Cool down
        sleep(60)
```

**Configuration**:
```yaml
# data-pipeline/configs/data_generation.yaml
scenarios:
  - healthy_baseline
  - latency_spike
  - error_spike
  - bimodal_latency
  - gradual_degradation
  - rate_limiting
  - cpu_bound
  - memory_leak
  - intermittent_errors
  - cascading_failures

samples_per_scenario: 100
test_duration_seconds: 300
cooldown_seconds: 60
output_dir: ./datasets/raw/
```

---

#### Task 1.4: Data Validation & Cleaning
**File**: `data-pipeline/storage/data_validator.py`

**Checks**:
- [ ] No missing values in critical fields
- [ ] Metrics within expected ranges
- [ ] Balanced class distribution
- [ ] Timestamp ordering
- [ ] Duplicate detection

---

### Deliverables

1. **Code**:
   - `data-pipeline/collectors/prometheus_exporter.py`
   - `data-pipeline/storage/dataset_builder.py`
   - `data-pipeline/storage/schema.py`
   - `data-pipeline/scripts/generate_training_data.py`
   - `data-pipeline/storage/data_validator.py`

2. **Data**:
   - `datasets/raw/` - Raw Prometheus exports (JSON)
   - `datasets/processed/` - Cleaned & labeled data (Parquet)
   - `datasets/training/` - Train/val/test splits (Parquet)

3. **Documentation**:
   - `data-pipeline/README.md` - Usage instructions
   - `docs/DATA_SCHEMA.md` - Detailed schema documentation

---

## 📋 Phase 2: Model Training

### Task 2.1: Bottleneck Detector (XGBoost)

**File**: `model-training/scripts/train_detector.py`

**Model Architecture**:
- **Algorithm**: XGBoost Classifier
- **Input Features**: Aggregated metrics (8-12 features)
- **Output**: Bottleneck type (multi-class classification)
- **Classes**: `healthy`, `latency`, `errors`, `rate_limit`, `resources`

**Training Pipeline**:
```python
# 1. Load data
train_df = load_parquet("datasets/training/train.parquet")

# 2. Feature engineering
features = extract_features(train_df)

# 3. Train model
model = xgb.XGBClassifier(
    objective='multi:softmax',
    num_class=5,
    max_depth=6,
    learning_rate=0.1,
    n_estimators=100
)
model.fit(X_train, y_train)

# 4. Evaluate
accuracy = model.score(X_test, y_test)
print(f"Accuracy: {accuracy:.2%}")

# 5. Save model
model.save_model("models/detector.json")
```

**Expected Performance**:
- Accuracy: >85% (POC target)
- Inference time: <10ms

---

### Task 2.2: Explanation Generator (Fine-tuned LLM)

**File**: `model-training/scripts/train_explainer.py`

**Base Model Options**:
1. **Llama-3.1-8B** (recommended)
2. **Mistral-7B**
3. **Phi-3-mini** (3.8B, faster)

**Fine-tuning Method**: LoRA (Low-Rank Adaptation)
- **Rank**: 16
- **Alpha**: 32
- **Target modules**: `q_proj`, `v_proj`, `o_proj`
- **Training**: 4-bit quantization (QLoRA)

**Training Data Format**:
```json
{
    "instruction": "Analyze the following performance metrics and explain any bottlenecks:",
    "input": "p50: 45ms, p95: 120ms, p99: 3500ms, error_rate: 2%, request_rate: 150/s",
    "output": "Detected p99 latency spike (3.5s vs baseline 120ms). This indicates tail latency issues affecting 1% of requests. Likely causes: GC pauses, network congestion, or cache misses. Recommendations: 1) Check GC logs, 2) Review network latency, 3) Analyze cache hit rates."
}
```

**Training Script**:
```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

# 1. Load base model (4-bit)
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.1-8B",
    load_in_4bit=True,
    device_map="auto"
)

# 2. Configure LoRA
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05,
    task_type="CAUSAL_LM"
)

# 3. Prepare model
model = prepare_model_for_kbit_training(model)
model = get_peft_model(model, lora_config)

# 4. Train
trainer = Trainer(
    model=model,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    args=training_args
)
trainer.train()

# 5. Save LoRA weights
model.save_pretrained("models/explainer_lora")
```

**Expected Performance**:
- BLEU score: >0.4
- Human evaluation: 4/5 quality rating
- Inference time: <2 seconds

---

## 📋 Phase 3: Inference Engine

### Task 3.1: FastAPI Service

**File**: `inference-engine/api/main.py`

**Endpoints**:
```python
@app.post("/analyze")
async def analyze_metrics(request: MetricsRequest):
    """Analyze performance metrics and detect bottlenecks"""
    
    # 1. Extract features
    features = extract_features(request.metrics)
    
    # 2. Detect bottleneck (XGBoost)
    bottleneck_type = detector.predict(features)
    confidence = detector.predict_proba(features).max()
    
    # 3. Generate explanation (LLM)
    if bottleneck_type != "healthy":
        explanation = explainer.generate(
            metrics=request.metrics,
            bottleneck_type=bottleneck_type
        )
    else:
        explanation = "No bottlenecks detected. System is healthy."
    
    return AnalysisResponse(
        bottleneck_detected=(bottleneck_type != "healthy"),
        bottleneck_type=bottleneck_type,
        confidence=confidence,
        explanation=explanation
    )
```

---

### Task 3.2: Model Loading & Caching

**File**: `inference-engine/detectors/bottleneck_detector.py`

```python
class BottleneckDetector:
    def __init__(self, model_path: str):
        self.model = xgb.Booster()
        self.model.load_model(model_path)
        
    def predict(self, features: np.ndarray):
        return self.model.predict(features)
```

**File**: `inference-engine/explainers/llm_explainer.py`

```python
class LLMExplainer:
    def __init__(self, base_model: str, lora_path: str):
        self.model = AutoModelForCausalLM.from_pretrained(
            base_model,
            load_in_4bit=True
        )
        self.model = PeftModel.from_pretrained(self.model, lora_path)
        self.tokenizer = AutoTokenizer.from_pretrained(base_model)
        
    def generate(self, metrics: dict, bottleneck_type: str):
        prompt = self._build_prompt(metrics, bottleneck_type)
        inputs = self.tokenizer(prompt, return_tensors="pt")
        outputs = self.model.generate(**inputs, max_length=512)
        return self.tokenizer.decode(outputs[0])
```

---

## 📋 Phase 4: Integration & Testing

### Task 4.1: End-to-End Testing

**Test Scenarios**:
1. **Known Chaos Scenarios**: Validate against ground truth
2. **Edge Cases**: Extreme values, missing data
3. **Performance**: Latency, throughput benchmarks
4. **Accuracy**: Precision, recall, F1-score

---

### Task 4.2: Live Integration

**Architecture**:
```
Chaos Generator → Prometheus → Inference Engine → Alerts
```

**Workflow**:
1. Chaos generator runs scenarios
2. Prometheus collects metrics
3. Inference engine polls Prometheus (every 30s)
4. Detects bottlenecks and generates alerts
5. Logs to file / sends to Grafana

---

## 🗓️ Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Phase 1: Data Pipeline | 3-5 days | 1,000+ training examples |
| Phase 2: Model Training | 3-5 days | Trained detector + explainer |
| Phase 3: Inference Engine | 2-3 days | FastAPI service |
| Phase 4: Integration | 2-3 days | End-to-end POC |
| **Total** | **10-16 days** | **Working POC** |

---

## 🚀 Getting Started

### Step 1: Create Directory Structure
```bash
cd /home/lostborion/Performange-analyzer-AI
mkdir -p data-pipeline/{collectors,storage,scripts,configs,datasets/{raw,processed,training}}
mkdir -p model-training/{notebooks,scripts,configs,models}
mkdir -p inference-engine/{api,detectors,explainers,models}
mkdir -p evaluation/{benchmarks,test_cases,reports}
mkdir -p docs
```

### Step 2: Install Dependencies
```bash
# Data pipeline
pip install prometheus-api-client pandas pyarrow

# Model training
pip install xgboost scikit-learn transformers peft bitsandbytes

# Inference engine
pip install fastapi uvicorn
```

### Step 3: Start with Phase 1
```bash
# Generate first batch of training data
python data-pipeline/scripts/generate_training_data.py
```

---

## ❓ Key Decisions Needed

Before we start implementation, please decide:

### 1. Model Selection
- [ ] **Option A**: Fine-tuned LLM only (Llama-3.1-8B)
- [ ] **Option B**: XGBoost + Small LLM (Phi-3-mini)
- [x] **Option C**: Hybrid (XGBoost + Llama-3.1-8B) ← **RECOMMENDED**

### 2. Dataset Size
- [ ] Minimum: 1,000 examples (100 per scenario)
- [ ] Better: 10,000 examples (1,000 per scenario)
- [ ] Production: 100,000+ examples

**Recommendation**: Start with 1,000, expand if needed

### 3. Training Infrastructure
- GPU: NVIDIA 3090 (24GB) ✅
- Sufficient for: 4-bit LoRA fine-tuning ✅
- Estimated training time: 2-4 hours

### 4. Success Criteria
- [ ] Detection accuracy > 85%
- [ ] Inference latency < 2 seconds
- [ ] Explanation quality: Human-validated
- [ ] Works with live chaos generator

---

## 📝 Next Actions

1. **Review this plan** - Any changes needed?
2. **Make key decisions** - Model, dataset size, success criteria
3. **Set up directory structure** - Run commands above
4. **Start Phase 1** - Build data pipeline
5. **Generate training data** - Run chaos generator extensively

---

**Ready to start building?** Let me know your decisions and we'll begin! 🚀
