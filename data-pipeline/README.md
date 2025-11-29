# Data Pipeline

Automated training data generation from chaos scenarios.

## 🎯 Purpose

This pipeline:
1. Runs chaos scenarios on the chaos generator
2. Collects metrics from Prometheus
3. Creates labeled training examples
4. Saves datasets in Parquet format
5. Splits data into train/val/test sets

## 📦 Components

### Collectors
- **`prometheus_exporter.py`** - Export metrics from Prometheus

### Storage
- **`schema.py`** - Data schema definitions
- **`dataset_builder.py`** - Build and save datasets

### Scripts
- **`generate_training_data.py`** - Main data generation script

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Chaos Generator

```bash
cd ../ratatoskr
docker-compose up -d
```

Verify services are running:
- Chaos API: http://localhost:8000
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

### 3. Generate Training Data

```bash
cd scripts
python generate_training_data.py
```

This will:
- Generate 10 examples per scenario (100 total)
- Each test runs for 5 minutes
- Total time: ~10 hours

### 4. Check Results

```bash
# View dataset statistics
python -c "
from storage.dataset_builder import DatasetBuilder
builder = DatasetBuilder('./datasets')
stats = builder.get_dataset_stats('training_data')
print(stats)
"
```

## 📊 Data Schema

### Training Example Structure

```python
{
    "id": str,                    # Unique example ID
    "timestamp": datetime,
    "scenario": str,              # Chaos scenario name
    "duration_seconds": int,
    
    # Aggregated metrics (5-minute window)
    "metrics": {
        "request_rate_mean": float,
        "request_rate_std": float,
        "p50_latency_mean": float,
        "p95_latency_mean": float,
        "p99_latency_mean": float,
        "p99_latency_max": float,
        "error_rate_mean": float,
        "error_rate_max": float,
        ...
    },
    
    # Labels for training
    "labels": {
        "has_bottleneck": bool,
        "bottleneck_type": str,   # "latency_spike", "error_spike", etc.
        "severity": str,           # "none", "low", "medium", "high", "critical"
        "root_cause": str,         # Detailed explanation
        "recommendations": list[str]
    }
}
```

## 🗂️ Output Structure

```
datasets/
├── raw/                    # Individual examples
│   ├── healthy_20251128_*.parquet
│   ├── latency_spike_*.parquet
│   └── ...
│
├── processed/              # Combined dataset
│   └── training_data.parquet
│
└── training/               # Train/val/test splits
    ├── train.parquet       # 70% of data
    ├── val.parquet         # 15% of data
    └── test.parquet        # 15% of data
```

## ⚙️ Configuration

Edit `configs/data_generation.yaml`:

```yaml
# Number of examples per scenario
samples_per_scenario: 10

# Test duration (seconds)
test_duration_seconds: 300

# Cooldown between tests (seconds)
cooldown_seconds: 60

# Scenarios to generate
scenarios:
  - healthy
  - latency_spike
  - error_spike
  # ... add more
```

## 📈 Scenarios

| Scenario | Bottleneck Type | Severity | Examples |
|----------|----------------|----------|----------|
| healthy | healthy | none | Baseline performance |
| latency_spike | latency_spike | high | p99 latency spikes |
| bimodal_latency | latency_bimodal | medium | Cache hit/miss patterns |
| gradual_degradation | latency_degradation | high | Memory leaks, resource exhaustion |
| error_spike | error_spike | critical | 5xx error bursts |
| intermittent | error_intermittent | medium | Flaky failures |
| rate_limited | rate_limit | medium | 429 errors |
| connection_exhaustion | resource_exhaustion | high | Connection pool exhaustion |
| cpu_bound | cpu_bound | high | CPU saturation |
| cascade_failure | cascade_failure | critical | Multiple failure modes |

## 🔧 Advanced Usage

### Generate Specific Scenarios

```python
from scripts.generate_training_data import TrainingDataGenerator

generator = TrainingDataGenerator()

# Generate only specific scenarios
generator.generate_dataset(
    scenarios=["healthy", "latency_spike"],
    samples_per_scenario=20,
    duration_seconds=300
)
```

### Export Single Example

```python
from collectors.prometheus_exporter import PrometheusExporter
from storage.dataset_builder import DatasetBuilder

exporter = PrometheusExporter()
builder = DatasetBuilder()

# Export metrics for last 5 minutes
data = exporter.export_scenario_metrics("latency_spike", duration_minutes=5)

# Create training example
example = builder.create_training_example(
    scenario="latency_spike",
    aggregated_metrics=data["aggregated"]
)

# Save
builder.append_to_dataset(example)
```

### Custom Train/Val/Test Split

```python
from storage.dataset_builder import DatasetBuilder

builder = DatasetBuilder()

splits = builder.create_train_val_test_split(
    dataset_name="training_data",
    train_ratio=0.8,
    val_ratio=0.1,
    test_ratio=0.1,
    random_seed=42
)
```

## 📊 Dataset Statistics

After generation, view statistics:

```python
from storage.dataset_builder import DatasetBuilder

builder = DatasetBuilder('./datasets')
stats = builder.get_dataset_stats('training_data')

print(f"Total examples: {stats['total_examples']}")
print(f"Scenarios: {stats['scenarios']}")
print(f"Bottleneck types: {stats['bottleneck_types']}")
print(f"File size: {stats['file_size_mb']:.2f} MB")
```

## ⏱️ Time Estimates

| Samples per Scenario | Total Examples | Estimated Time |
|---------------------|----------------|----------------|
| 10 | 100 | ~10 hours |
| 50 | 500 | ~50 hours |
| 100 | 1,000 | ~100 hours |

**Note**: Each example takes ~6 minutes (5 min test + 1 min cooldown)

## 🐛 Troubleshooting

### Prometheus Not Accessible

```bash
# Check if Prometheus is running
curl http://localhost:9090/-/healthy

# Restart if needed
cd ../ratatoskr
docker-compose restart prometheus
```

### Chaos Generator Not Responding

```bash
# Check chaos generator status
curl http://localhost:8000/health

# Restart if needed
docker-compose restart ratatoskr
```

### No Metrics Data

- Ensure chaos generator has been running for at least 5 minutes
- Check Prometheus targets: http://localhost:9090/targets
- Verify metrics are being scraped: http://localhost:9090/graph

## 📝 Next Steps

After generating data:

1. **Validate dataset**:
   ```bash
   python -c "import pandas as pd; df = pd.read_parquet('datasets/training/train.parquet'); print(df.info())"
   ```

2. **Explore data**:
   ```bash
   jupyter notebook
   # Open notebooks/explore_dataset.ipynb
   ```

3. **Train models**:
   ```bash
   cd ../model-training
   python scripts/train_detector.py
   ```

## 🎯 Success Criteria

- [ ] 100+ training examples generated
- [ ] All 10 scenarios represented
- [ ] Balanced class distribution
- [ ] No missing values in critical fields
- [ ] Train/val/test splits created
- [ ] Dataset statistics look reasonable

---

**Status**: ✅ Ready to generate training data!

**Estimated time for 100 examples**: ~10 hours
