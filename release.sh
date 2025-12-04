#!/bin/bash
# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
set -e

echo "🚀 Starting Release Process..."

# 1. Clean previous builds
echo "🧹 Cleaning up..."
rm -rf dist/ build/ *.egg-info

# 2. Run tests
echo "🧪 Running tests..."
.venv/bin/pytest tests

# 3. Build wheel
echo "📦 Building wheel..."
.venv/bin/python setup.py sdist bdist_wheel

# 4. Check package
echo "🔍 Checking package..."
.venv/bin/pip install twine
.venv/bin/twine check dist/*

echo "✅ Release build complete!"
echo "To publish to PyPI, run: twine upload dist/*"
