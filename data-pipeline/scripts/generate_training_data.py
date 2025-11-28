"""Automated training data generation from chaos scenarios."""
import sys
import time
import requests
from pathlib import Path
from datetime import datetime
import logging

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from collectors.prometheus_exporter import PrometheusExporter
from storage.dataset_builder import DatasetBuilder

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TrainingDataGenerator:
    """Generate training data by running chaos scenarios."""
    
    def __init__(
        self,
        chaos_api_url: str = "http://localhost:8000",
        prometheus_url: str = "http://localhost:9090",
        output_dir: str = "./datasets"
    ):
        """Initialize training data generator.
        
        Args:
            chaos_api_url: URL of chaos generator API
            prometheus_url: URL of Prometheus server
            output_dir: Directory to save datasets
        """
        self.chaos_api_url = chaos_api_url
        self.exporter = PrometheusExporter(prometheus_url)
        self.builder = DatasetBuilder(output_dir)
        
    def activate_scenario(self, scenario: str) -> bool:
        """Activate a chaos scenario.
        
        Args:
            scenario: Scenario name
            
        Returns:
            True if successful, False otherwise
        """
        url = f"{self.chaos_api_url}/chaos/scenario/{scenario}"
        
        try:
            response = requests.post(url, timeout=10)
            response.raise_for_status()
            logger.info(f"✅ Activated scenario: {scenario}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to activate scenario '{scenario}': {e}")
            return False
    
    def run_load_test(self, duration_seconds: int = 300, rps: int = 50) -> bool:
        """Run a load test using simple requests loop.
        
        Args:
            duration_seconds: Duration of the test
            rps: Requests per second (approximate)
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"🔥 Running load test: {duration_seconds}s @ {rps} RPS")
        
        import threading
        import time
        
        stop_event = threading.Event()
        
        def load_generator():
            while not stop_event.is_set():
                try:
                    # Send request to chaos generator work endpoint
                    requests.get(f"{self.chaos_api_url}/api/work", timeout=1)
                except Exception:
                    pass
                
                # Sleep to match RPS
                time.sleep(1.0 / rps)
        
        # Start load generator threads (use 5 threads to maintain RPS)
        threads = []
        for _ in range(5):
            t = threading.Thread(target=load_generator)
            t.daemon = True
            t.start()
            threads.append(t)
            
        # Wait for duration
        time.sleep(duration_seconds)
        
        # Stop threads
        stop_event.set()
        for t in threads:
            t.join(timeout=1.0)
        
        logger.info("✅ Load test completed")
        return True
    
    def generate_example(
        self,
        scenario: str,
        duration_seconds: int = 300,
        cooldown_seconds: int = 60
    ) -> bool:
        """Generate a single training example for a scenario.
        
        Args:
            scenario: Chaos scenario name
            duration_seconds: Duration to run the scenario
            cooldown_seconds: Cooldown period after scenario
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 Generating training example for: {scenario}")
        logger.info(f"{'='*60}")
        
        # 1. Activate scenario
        if not self.activate_scenario(scenario):
            return False
        
        # 2. Wait for scenario to stabilize
        logger.info("⏳ Waiting 30s for scenario to stabilize...")
        time.sleep(30)
        
        # 3. Run load test
        if not self.run_load_test(duration_seconds):
            return False
        
        # 4. Export metrics from Prometheus
        logger.info("📈 Exporting metrics from Prometheus...")
        scenario_data = self.exporter.export_scenario_metrics(
            scenario_name=scenario,
            duration_minutes=duration_seconds // 60
        )
        
        if not scenario_data["aggregated"]:
            logger.error("❌ No metrics data available")
            return False
        
        # 5. Create training example
        logger.info("💾 Creating training example...")
        example = self.builder.create_training_example(
            scenario=scenario,
            aggregated_metrics=scenario_data["aggregated"],
            duration_seconds=duration_seconds
        )
        
        # 6. Save to dataset
        self.builder.append_to_dataset(example, dataset_name="training_data")
        
        # 7. Cooldown
        logger.info(f"😴 Cooldown period: {cooldown_seconds}s...")
        time.sleep(cooldown_seconds)
        
        logger.info(f"✅ Successfully generated example for '{scenario}'")
        
        return True
    
    def generate_dataset(
        self,
        scenarios: list[str],
        samples_per_scenario: int = 10,
        duration_seconds: int = 300,
        cooldown_seconds: int = 60
    ) -> None:
        """Generate a complete training dataset.
        
        Args:
            scenarios: List of scenario names
            samples_per_scenario: Number of examples per scenario
            duration_seconds: Duration for each test run
            cooldown_seconds: Cooldown between tests
        """
        logger.info(f"\n{'#'*60}")
        logger.info(f"🚀 STARTING TRAINING DATA GENERATION")
        logger.info(f"{'#'*60}")
        logger.info(f"Scenarios: {len(scenarios)}")
        logger.info(f"Samples per scenario: {samples_per_scenario}")
        logger.info(f"Total examples to generate: {len(scenarios) * samples_per_scenario}")
        logger.info(f"Estimated time: {len(scenarios) * samples_per_scenario * (duration_seconds + cooldown_seconds) / 3600:.1f} hours")
        logger.info(f"{'#'*60}\n")
        
        # Check connectivity
        if not self.exporter.health_check():
            logger.error("❌ Prometheus is not accessible. Aborting.")
            return
        
        try:
            response = requests.get(f"{self.chaos_api_url}/health", timeout=5)
            response.raise_for_status()
        except requests.exceptions.RequestException:
            logger.error("❌ Chaos generator is not accessible. Aborting.")
            return
        
        # Generate examples
        total_generated = 0
        total_failed = 0
        
        for scenario in scenarios:
            logger.info(f"\n{'='*60}")
            logger.info(f"📦 Scenario: {scenario} ({samples_per_scenario} samples)")
            logger.info(f"{'='*60}")
            
            for i in range(samples_per_scenario):
                logger.info(f"\n--- Sample {i+1}/{samples_per_scenario} ---")
                
                success = self.generate_example(
                    scenario=scenario,
                    duration_seconds=duration_seconds,
                    cooldown_seconds=cooldown_seconds
                )
                
                if success:
                    total_generated += 1
                else:
                    total_failed += 1
                
                # Show progress
                logger.info(f"\n📊 Progress: {total_generated} generated, {total_failed} failed")
        
        # Final summary
        logger.info(f"\n{'#'*60}")
        logger.info(f"✅ TRAINING DATA GENERATION COMPLETE")
        logger.info(f"{'#'*60}")
        logger.info(f"Total generated: {total_generated}")
        logger.info(f"Total failed: {total_failed}")
        
        # Show dataset stats
        stats = self.builder.get_dataset_stats("training_data")
        logger.info(f"\n📊 Dataset Statistics:")
        logger.info(f"   Total examples: {stats.get('total_examples', 0)}")
        logger.info(f"   File size: {stats.get('file_size_mb', 0):.2f} MB")
        logger.info(f"   Scenarios: {stats.get('scenarios', {})}")
        
        # Create train/val/test splits
        logger.info(f"\n🔀 Creating train/val/test splits...")
        try:
            splits = self.builder.create_train_val_test_split("training_data")
            logger.info(f"   Train: {splits['train']}")
            logger.info(f"   Val: {splits['val']}")
            logger.info(f"   Test: {splits['test']}")
        except Exception as e:
            logger.error(f"   Failed to create splits: {e}")


def main():
    """Main entry point."""
    # List of scenarios to generate data for
    scenarios = [
        "healthy",
        "latency_spike",
        "bimodal_latency",
        "gradual_degradation",
        "error_spike",
        "intermittent",
        "rate_limited",
        "connection_exhaustion",
        "cpu_bound",
        "cascade_failure"
    ]
    
    # Configuration
    SAMPLES_PER_SCENARIO = 10  # Start with 10 samples per scenario (100 total)
    DURATION_SECONDS = 300     # 5 minutes per test
    COOLDOWN_SECONDS = 60      # 1 minute cooldown
    
    # Initialize generator
    generator = TrainingDataGenerator(
        chaos_api_url="http://localhost:8000",
        prometheus_url="http://localhost:9090",
        output_dir="./datasets"
    )
    
    # Generate dataset
    generator.generate_dataset(
        scenarios=scenarios,
        samples_per_scenario=SAMPLES_PER_SCENARIO,
        duration_seconds=DURATION_SECONDS,
        cooldown_seconds=COOLDOWN_SECONDS
    )


if __name__ == "__main__":
    main()
