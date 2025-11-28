"""Dataset builder for creating training datasets from Prometheus metrics."""
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import uuid
import logging

from .schema import (
    TrainingExample,
    AggregatedMetrics,
    TrainingLabels,
    get_labels_for_scenario
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatasetBuilder:
    """Build training datasets from chaos generator metrics."""
    
    def __init__(self, output_dir: str = "./datasets"):
        """Initialize dataset builder.
        
        Args:
            output_dir: Directory to save datasets
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.raw_dir = self.output_dir / "raw"
        self.processed_dir = self.output_dir / "processed"
        self.training_dir = self.output_dir / "training"
        
        for dir_path in [self.raw_dir, self.processed_dir, self.training_dir]:
            dir_path.mkdir(exist_ok=True)
    
    def create_training_example(
        self,
        scenario: str,
        aggregated_metrics: Dict[str, Dict[str, float]],
        duration_seconds: int = 300
    ) -> TrainingExample:
        """Create a training example from aggregated metrics.
        
        Args:
            scenario: Chaos scenario name
            aggregated_metrics: Aggregated metrics from Prometheus
            duration_seconds: Duration of the test run
            
        Returns:
            TrainingExample with metrics and labels
        """
        # Generate unique ID
        example_id = f"{scenario}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Extract metrics
        metrics = AggregatedMetrics(
            # Request rate
            request_rate_mean=aggregated_metrics.get("request_rate", {}).get("mean", 0.0),
            request_rate_std=aggregated_metrics.get("request_rate", {}).get("std", 0.0),
            request_rate_min=aggregated_metrics.get("request_rate", {}).get("min", 0.0),
            request_rate_max=aggregated_metrics.get("request_rate", {}).get("max", 0.0),
            
            # Latency p50
            p50_latency_mean=aggregated_metrics.get("p50_latency", {}).get("mean", 0.0),
            p50_latency_std=aggregated_metrics.get("p50_latency", {}).get("std", 0.0),
            
            # Latency p95
            p95_latency_mean=aggregated_metrics.get("p95_latency", {}).get("mean", 0.0),
            p95_latency_std=aggregated_metrics.get("p95_latency", {}).get("std", 0.0),
            
            # Latency p99
            p99_latency_mean=aggregated_metrics.get("p99_latency", {}).get("mean", 0.0),
            p99_latency_std=aggregated_metrics.get("p99_latency", {}).get("std", 0.0),
            p99_latency_max=aggregated_metrics.get("p99_latency", {}).get("max", 0.0),
            
            # Error rate
            error_rate_mean=aggregated_metrics.get("error_rate", {}).get("mean", 0.0),
            error_rate_std=aggregated_metrics.get("error_rate", {}).get("std", 0.0),
            error_rate_max=aggregated_metrics.get("error_rate", {}).get("max", 0.0),
            
            # Concurrent requests
            concurrent_requests_mean=aggregated_metrics.get("concurrent_requests", {}).get("mean", 0.0),
            concurrent_requests_max=aggregated_metrics.get("concurrent_requests", {}).get("max", 0.0),
        )
        
        # Get labels for this scenario
        labels = get_labels_for_scenario(scenario)
        
        # Create training example
        example = TrainingExample(
            id=example_id,
            timestamp=datetime.utcnow(),
            scenario=scenario,
            duration_seconds=duration_seconds,
            metrics=metrics,
            labels=labels
        )
        
        logger.info(f"Created training example: {example_id} for scenario '{scenario}'")
        
        return example
    
    def save_example(
        self,
        example: TrainingExample,
        output_file: Optional[str] = None
    ) -> Path:
        """Save a single training example to Parquet.
        
        Args:
            example: TrainingExample to save
            output_file: Optional output filename (default: auto-generated)
            
        Returns:
            Path to saved file
        """
        if output_file is None:
            output_file = f"{example.id}.parquet"
        
        output_path = self.raw_dir / output_file
        
        # Convert to DataFrame
        df = pd.DataFrame([self._flatten_example(example)])
        
        # Save to Parquet
        df.to_parquet(output_path, index=False, engine='pyarrow')
        
        logger.info(f"Saved example to {output_path}")
        
        return output_path
    
    def append_to_dataset(
        self,
        example: TrainingExample,
        dataset_name: str = "training_data"
    ) -> None:
        """Append a training example to an existing dataset.
        
        Args:
            example: TrainingExample to append
            dataset_name: Name of the dataset file
        """
        dataset_path = self.processed_dir / f"{dataset_name}.parquet"
        
        # Flatten example
        flattened = self._flatten_example(example)
        new_df = pd.DataFrame([flattened])
        
        # Append or create
        if dataset_path.exists():
            existing_df = pd.read_parquet(dataset_path)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df
        
        # Save
        combined_df.to_parquet(dataset_path, index=False, engine='pyarrow')
        
        logger.info(f"Appended example to {dataset_path} (total: {len(combined_df)} examples)")
    
    def _flatten_example(self, example: TrainingExample) -> Dict:
        """Flatten a training example into a flat dictionary for DataFrame.
        
        Args:
            example: TrainingExample to flatten
            
        Returns:
            Flattened dictionary
        """
        flattened = {
            "id": example.id,
            "timestamp": example.timestamp,
            "scenario": example.scenario,
            "duration_seconds": example.duration_seconds,
        }
        
        # Add metrics with prefix
        metrics_dict = example.metrics.to_dict()
        for key, value in metrics_dict.items():
            flattened[f"metric_{key}"] = value
        
        # Add labels
        labels_dict = example.labels.to_dict()
        flattened["label_has_bottleneck"] = labels_dict["has_bottleneck"]
        flattened["label_bottleneck_type"] = labels_dict["bottleneck_type"]
        flattened["label_severity"] = labels_dict["severity"]
        flattened["label_root_cause"] = labels_dict["root_cause"]
        flattened["label_recommendations"] = "|".join(labels_dict["recommendations"])
        
        return flattened
    
    def create_train_val_test_split(
        self,
        dataset_name: str = "training_data",
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        random_seed: int = 42
    ) -> Dict[str, Path]:
        """Split dataset into train/validation/test sets.
        
        Args:
            dataset_name: Name of the dataset to split
            train_ratio: Proportion for training set
            val_ratio: Proportion for validation set
            test_ratio: Proportion for test set
            random_seed: Random seed for reproducibility
            
        Returns:
            Dictionary with paths to train/val/test files
        """
        assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, \
            "Ratios must sum to 1.0"
        
        dataset_path = self.processed_dir / f"{dataset_name}.parquet"
        
        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset not found: {dataset_path}")
        
        # Load dataset
        df = pd.read_parquet(dataset_path)
        
        # Shuffle
        df = df.sample(frac=1, random_state=random_seed).reset_index(drop=True)
        
        # Calculate split indices
        n = len(df)
        train_end = int(n * train_ratio)
        val_end = train_end + int(n * val_ratio)
        
        # Split
        train_df = df[:train_end]
        val_df = df[train_end:val_end]
        test_df = df[val_end:]
        
        # Save splits
        paths = {}
        
        train_path = self.training_dir / "train.parquet"
        train_df.to_parquet(train_path, index=False, engine='pyarrow')
        paths["train"] = train_path
        logger.info(f"Saved training set: {len(train_df)} examples → {train_path}")
        
        val_path = self.training_dir / "val.parquet"
        val_df.to_parquet(val_path, index=False, engine='pyarrow')
        paths["val"] = val_path
        logger.info(f"Saved validation set: {len(val_df)} examples → {val_path}")
        
        test_path = self.training_dir / "test.parquet"
        test_df.to_parquet(test_path, index=False, engine='pyarrow')
        paths["test"] = test_path
        logger.info(f"Saved test set: {len(test_df)} examples → {test_path}")
        
        return paths
    
    def get_dataset_stats(self, dataset_name: str = "training_data") -> Dict:
        """Get statistics about a dataset.
        
        Args:
            dataset_name: Name of the dataset
            
        Returns:
            Dictionary with dataset statistics
        """
        dataset_path = self.processed_dir / f"{dataset_name}.parquet"
        
        if not dataset_path.exists():
            return {"error": "Dataset not found"}
        
        df = pd.read_parquet(dataset_path)
        
        stats = {
            "total_examples": len(df),
            "scenarios": df["scenario"].value_counts().to_dict(),
            "bottleneck_types": df["label_bottleneck_type"].value_counts().to_dict(),
            "severity_distribution": df["label_severity"].value_counts().to_dict(),
            "date_range": {
                "start": df["timestamp"].min().isoformat(),
                "end": df["timestamp"].max().isoformat()
            },
            "file_size_mb": dataset_path.stat().st_size / (1024 * 1024)
        }
        
        return stats


if __name__ == "__main__":
    # Test the dataset builder
    builder = DatasetBuilder(output_dir="./datasets")
    
    # Example: Create a dummy training example
    dummy_metrics = {
        "request_rate": {"mean": 50.0, "std": 5.0, "min": 40.0, "max": 60.0},
        "p50_latency": {"mean": 0.045, "std": 0.005, "min": 0.035, "max": 0.055},
        "p95_latency": {"mean": 0.120, "std": 0.010, "min": 0.100, "max": 0.140},
        "p99_latency": {"mean": 0.150, "std": 0.020, "min": 0.120, "max": 0.180},
        "error_rate": {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0},
        "concurrent_requests": {"mean": 10.0, "std": 2.0, "min": 5.0, "max": 15.0}
    }
    
    example = builder.create_training_example(
        scenario="healthy",
        aggregated_metrics=dummy_metrics,
        duration_seconds=300
    )
    
    print(f"✅ Created example: {example.id}")
    print(f"   Scenario: {example.scenario}")
    print(f"   Bottleneck: {example.labels.bottleneck_type.value}")
    print(f"   Severity: {example.labels.severity.value}")
