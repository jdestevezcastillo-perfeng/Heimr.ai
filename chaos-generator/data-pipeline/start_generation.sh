#!/bin/bash

# Quick start script for training data generation

set -e

echo "🚀 Heimr.ai - Training Data Generation"
echo "======================================================"
echo ""

# Check if chaos generator is running
echo "📡 Checking chaos generator..."
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ Chaos generator is not running!"
    echo "   Start it with: cd ../chaos-generator && docker-compose up -d"
    exit 1
fi
echo "✅ Chaos generator is running"

# Check if Prometheus is running
echo "📡 Checking Prometheus..."
if ! curl -s http://localhost:9090/-/healthy > /dev/null 2>&1; then
    echo "❌ Prometheus is not running!"
    echo "   Start it with: cd ../chaos-generator && docker-compose up -d"
    exit 1
fi
echo "✅ Prometheus is running"

# Activate virtual environment
echo ""
echo "🐍 Activating virtual environment..."
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installing dependencies..."
    pip install -q -r requirements.txt
else
    source venv/bin/activate
fi
echo "✅ Virtual environment activated"

# Show configuration
echo ""
echo "⚙️  Configuration:"
echo "   Scenarios: 10"
echo "   Samples per scenario: 10"
echo "   Total examples: 100"
echo "   Test duration: 5 minutes"
echo "   Cooldown: 1 minute"
echo "   Estimated time: ~10 hours"
echo ""

# Ask for confirmation
read -p "Start data generation? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Run data generation
echo ""
echo "🔥 Starting data generation..."
echo "   You can monitor progress in Grafana: http://localhost:3000"
echo "   Press Ctrl+C to stop (data will be saved)"
echo ""

cd scripts
python generate_training_data.py

echo ""
echo "✅ Data generation complete!"
echo ""
echo "📊 Check results:"
echo "   Dataset: datasets/processed/training_data.parquet"
echo "   Train/val/test: datasets/training/"
echo ""
echo "Next steps:"
echo "   1. Review dataset statistics"
echo "   2. Train models: cd ../model-training"
