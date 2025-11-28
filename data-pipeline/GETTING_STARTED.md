# 🎉 Data Pipeline - Ready to Generate Training Data!

## ✅ What's Been Built

### Components Created:
1. **Prometheus Exporter** (`collectors/prometheus_exporter.py`)
   - Queries Prometheus for metrics
   - Exports time-series data
   - Aggregates statistics

2. **Data Schema** (`storage/schema.py`)
   - Training example structure
   - Bottleneck type definitions
   - Scenario-to-label mappings
   - Root cause explanations

3. **Dataset Builder** (`storage/dataset_builder.py`)
   - Creates training examples
   - Saves to Parquet format
   - Creates train/val/test splits

4. **Data Generation Script** (`scripts/generate_training_data.py`)
   - Orchestrates chaos scenarios
   - Runs load tests
   - Collects and saves data

5. **Quick Test** (`scripts/quick_test.py`)
   - Generate 3 examples for testing
   - Faster validation (~15 minutes)

6. **Start Script** (`start_generation.sh`)
   - Automated startup with health checks
   - Full dataset generation (100 examples)

---

## 🚀 Quick Start

### Option 1: Quick Test (Recommended First)

Generate 3 examples to validate the pipeline (~15 minutes):

```bash
cd /home/lostborion/Performange-analyzer-AI/data-pipeline
source venv/bin/activate
python scripts/quick_test.py
```

This will generate:
- 1 healthy example
- 1 latency_spike example  
- 1 error_spike example

**Estimated time**: ~15 minutes (3 min per test + 30s cooldown)

---

### Option 2: Full Dataset Generation

Generate 100 training examples (~10 hours):

```bash
cd /home/lostborion/Performange-analyzer-AI/data-pipeline
./start_generation.sh
```

This will generate:
- 10 examples per scenario
- 10 scenarios total
- 100 training examples

**Estimated time**: ~10 hours (5 min per test + 1 min cooldown)

---

## 📊 What Gets Generated

### Data Structure:
```
datasets/
├── raw/                          # Individual examples
│   ├── healthy_*.parquet
│   ├── latency_spike_*.parquet
│   └── ...
│
├── processed/                    # Combined dataset
│   └── training_data.parquet     # All examples in one file
│
└── training/                     # Train/val/test splits
    ├── train.parquet             # 70% of data
    ├── val.parquet               # 15% of data
    └── test.parquet              # 15% of data
```

### Example Data:
```python
{
    "id": "latency_spike_20251128_180306_a1b2c3d4",
    "timestamp": "2025-11-28T18:03:06",
    "scenario": "latency_spike",
    "duration_seconds": 300,
    
    "metrics": {
        "request_rate_mean": 50.2,
        "p50_latency_mean": 0.045,
        "p95_latency_mean": 0.120,
        "p99_latency_mean": 2.850,  # ← Spike detected!
        "error_rate_mean": 0.02,
        ...
    },
    
    "labels": {
        "has_bottleneck": true,
        "bottleneck_type": "latency_spike",
        "severity": "high",
        "root_cause": "Detected p99 latency spike...",
        "recommendations": ["Check GC logs", "Review network latency", ...]
    }
}
```

---

## 🎯 Scenarios Being Generated

| Scenario | Type | Severity | What It Tests |
|----------|------|----------|---------------|
| healthy | healthy | none | Baseline performance |
| latency_spike | latency_spike | high | p99 latency anomalies |
| bimodal_latency | latency_bimodal | medium | Cache hit/miss patterns |
| gradual_degradation | latency_degradation | high | Memory leaks |
| error_spike | error_spike | critical | 5xx error bursts |
| intermittent | error_intermittent | medium | Flaky failures |
| rate_limited | rate_limit | medium | 429 errors |
| connection_exhaustion | resource_exhaustion | high | Connection pool issues |
| cpu_bound | cpu_bound | high | CPU saturation |
| cascade_failure | cascade_failure | critical | Multiple failures |

---

## 📈 Monitoring Progress

### Grafana Dashboard
Monitor data generation in real-time:
- **URL**: http://localhost:3000
- **Dashboard**: Chaos Generator Dashboard
- **Watch**: Active scenario, latency, error rate

### Logs
The generation script logs progress:
```
📊 Generating training example for: latency_spike
✅ Activated scenario: latency_spike
⏳ Waiting 30s for scenario to stabilize...
🔥 Running load test: 300s @ 50 RPS
📈 Exporting metrics from Prometheus...
💾 Creating training example...
✅ Successfully generated example for 'latency_spike'
```

---

## ✅ Validation

After generation, validate the data:

```bash
source venv/bin/activate
python -c "
from storage.dataset_builder import DatasetBuilder
builder = DatasetBuilder('./datasets')
stats = builder.get_dataset_stats('training_data')

print(f'Total examples: {stats[\"total_examples\"]}')
print(f'Scenarios: {stats[\"scenarios\"]}')
print(f'File size: {stats[\"file_size_mb\"]:.2f} MB')
"
```

Expected output:
```
Total examples: 3 (or 100 for full dataset)
Scenarios: {'healthy': 1, 'latency_spike': 1, 'error_spike': 1}
File size: 0.05 MB
```

---

## 🐛 Troubleshooting

### "Prometheus is not accessible"
```bash
cd ../chaos-generator
docker-compose ps
docker-compose restart prometheus
```

### "Chaos generator is not accessible"
```bash
cd ../chaos-generator
docker-compose ps
docker-compose restart chaos-generator
```

### "No metrics data available"
- Wait 5 minutes after starting chaos generator
- Check Prometheus targets: http://localhost:9090/targets
- Ensure chaos generator is receiving traffic

---

## ⏱️ Time Estimates

| Task | Examples | Time |
|------|----------|------|
| Quick test | 3 | ~15 minutes |
| Small dataset | 30 | ~3 hours |
| POC dataset | 100 | ~10 hours |
| Production dataset | 1,000 | ~100 hours |

**Note**: You can run this overnight or in the background!

---

## 🎯 Next Steps

### After Quick Test (3 examples):
1. ✅ Validate data looks correct
2. ✅ Check Parquet files are created
3. ✅ Review metrics and labels
4. 🚀 Run full dataset generation

### After Full Dataset (100 examples):
1. ✅ Create train/val/test splits
2. ✅ Explore data in Jupyter notebook
3. 🚀 Start model training (Phase 2)

---

## 📝 Current Status

- [x] Data pipeline components built
- [x] Prometheus exporter tested
- [x] Virtual environment set up
- [x] Dependencies installed
- [ ] Quick test run (3 examples)
- [ ] Full dataset generated (100 examples)
- [ ] Train/val/test splits created

---

## 🚀 Ready to Start!

### Recommended: Start with Quick Test

```bash
cd /home/lostborion/Performange-analyzer-AI/data-pipeline
source venv/bin/activate
python scripts/quick_test.py
```

This will:
1. ✅ Validate the pipeline works
2. ✅ Generate 3 training examples
3. ✅ Take only ~15 minutes
4. ✅ Let you review data quality

**Then**, if everything looks good, run the full generation:

```bash
./start_generation.sh
```

---

**While data is generating, you can**:
- Review the documentation
- Explore the code
- Monitor progress in Grafana
- Plan the model training phase

**The data generation runs in the background and saves progress continuously!** 🎉
