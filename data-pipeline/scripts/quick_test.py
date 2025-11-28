#!/usr/bin/env python3
"""Quick test - generate a few training examples."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.generate_training_data import TrainingDataGenerator

def main():
    print("🧪 Quick Test - Generating 3 training examples")
    print("=" * 60)
    print()
    
    # Test scenarios
    test_scenarios = [
        "healthy",
        "latency_spike",
        "error_spike"
    ]
    
    generator = TrainingDataGenerator(
        chaos_api_url="http://localhost:8000",
        prometheus_url="http://localhost:9090",
        output_dir="./datasets"
    )
    
    # Generate 1 example per scenario (quick test)
    generator.generate_dataset(
        scenarios=test_scenarios,
        samples_per_scenario=1,
        duration_seconds=60,   # 1 minute (fast test)
        cooldown_seconds=10    # 10 seconds cooldown
    )
    
    print()
    print("✅ Quick test complete!")
    print()
    print("📊 Check the results:")
    print("   Dataset: datasets/processed/training_data.parquet")
    print()
    print("To generate the full dataset (100 examples):")
    print("   ./start_generation.sh")

if __name__ == "__main__":
    main()
