# Contributing to Heimr.ai

Thank you for your interest in contributing to Heimr! This document provides guidelines and instructions for contributing to the project.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Project Structure](#project-structure)
5. [Making Changes](#making-changes)
6. [Testing](#testing)
7. [Submitting Changes](#submitting-changes)
8. [Style Guidelines](#style-guidelines)

---

## Code of Conduct

We are committed to providing a welcoming and inclusive environment. Please be respectful and professional in all interactions.

---

## Getting Started

### Prerequisites

- Python 3.8+
- Git
- (Optional) Ollama for local LLM testing
- (Optional) Docker for containerized testing

### Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/Heimr.ai.git
cd Heimr.ai
```

---

## Development Setup

### 1. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Dependencies

```bash
# Install Heimr in development mode
pip install -e .

# Install development dependencies
pip install -r requirements_dev.txt
```

### 3. Install Pre-commit Hooks (Optional)

```bash
pre-commit install
```

### 4. Set Up Ollama (Optional)

For testing LLM integration locally:

```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull Llama 3.1
ollama pull llama3.1:8b
```

---

## Project Structure

```
Heimr.ai/
├── heimr/                     # Main package
│   ├── parsers/               # Load test result parsers
│   │   ├── base.py            # Base parser class
│   │   ├── jtl.py             # JMeter parser
│   │   ├── k6.py              # k6 parser
│   │   ├── gatling.py         # Gatling parser
│   │   ├── locust.py          # Locust parser
│   │   └── har.py             # HAR (HTTP Archive) parser
│   ├── reporters/             # Output formatters
│   │   ├── github.py          # GitHub Actions summary
│   │   └── junit.py           # JUnit XML for CI/CD
│   ├── cli.py                 # CLI interface & orchestration
│   ├── detector.py            # Statistical anomaly detection
│   ├── kpi.py                 # KPI calculations
│   ├── llm.py                 # LLM integration (Ollama, OpenAI, Anthropic)
│   ├── comparator.py          # Baseline comparison engine
│   ├── pdf_generator.py       # PDF report generation
│   ├── setup_llm.py           # LLM setup wizard
│   ├── prometheus.py          # Prometheus metrics client
│   ├── loki.py                # Loki logs client
│   └── tempo.py               # Tempo traces client
├── docs/                      # Documentation
│   ├── WIKI.md                # Wiki index
│   └── wiki/                  # Wiki pages (10 pages)
├── tests/                     # Test suite
├── load-tests/                # Load test scripts (k6, JMeter, Gatling, Locust)
├── demos/                     # Demo scripts and examples
├── website/                   # Landing page (heimr.ai)
├── setup.py                   # Package configuration
├── requirements.txt           # Dependencies
└── heimr.yaml.example         # Example configuration file
```

---

## Making Changes

### Types of Contributions

We welcome:
- 🐛 **Bug fixes**
- ✨ **New features** (parsers, integrations, scenarios)
- 📝 **Documentation improvements**
- 🧪 **Test coverage**
- 🎨 **Code quality improvements**

### Workflow

1. **Create a branch**:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/bug-description
   ```

2. **Make your changes**:
   - Write clean, readable code
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes**:
   ```bash
   # Run tests
   pytest
   
   # Run linting
   flake8 heimr/
   black heimr/ --check
   
   # Test with mock data
   python scripts/validate_scenarios.py --llm-url http://localhost:11434/v1 --llm-model llama3.1:8b
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add support for Artillery.io parser"
   ```

   Use [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` New feature
   - `fix:` Bug fix
   - `docs:` Documentation
   - `test:` Tests
   - `refactor:` Code refactoring
   - `chore:` Maintenance

5. **Push and create PR**:
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a Pull Request on GitHub.

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_parsers.py

# Run with coverage
pytest --cov=heimr --cov-report=html
```

### Writing Tests

Place tests in `tests/` directory:

```python
# tests/test_detector.py
import pytest
from heimr.detector import detect_anomalies

def test_detects_latency_spike():
    # Create test data with spike
    data = create_test_data_with_spike()
    
    # Run detection
    signals = detect_anomalies(data)
    
    # Assert spike was detected
    assert any("Anomalies" in s for s in signals)
```

### Development Scripts

The `scripts/` directory contains utilities for testing and validating Heimr. See [scripts/README.md](scripts/README.md) for full documentation.

#### Generate Mock Data

Creates synthetic load test results and observability data for all 140+ failure scenarios:

```bash
python scripts/generate_mock_data.py
```

This generates `data/mocks/<SCENARIO_ID>/` directories with JMeter, k6, Gatling, Locust files plus Prometheus/Loki/Tempo snapshots.

#### Quick Validation (No LLM)

Fast check that anomaly detection works correctly. Good for CI:

```bash
python scripts/quick_validate.py
```

- `API-001` (Healthy) should `PASS`
- All failure scenarios should `FAIL`

#### Full Validation (With LLM)

Runs complete analysis including AI-generated reports:

```bash
# Local Ollama
python scripts/validate_scenarios.py \
  --llm-url http://localhost:11434/v1 \
  --llm-model llama3.1:8b

# OpenAI
python scripts/validate_scenarios.py \
  --provider openai \
  --api-key $OPENAI_API_KEY
```

#### Report Analysis

Cross-reference reports with expected behavior:

```bash
python scripts/analyze_reports.py
python scripts/validate_mock_reports.py
```

### Load Test Scripts

The `load-tests/` directory contains sample load test scripts for all supported tools:

```
load-tests/
├── k6/          # k6 JavaScript scripts
├── jmeter/      # JMeter JMX files
├── gatling/     # Gatling Scala simulations
└── locust/      # Locust Python scripts
```

Use these as reference implementations or to test Heimr against real load test output.

---

## Submitting Changes

### Pull Request Guidelines

**Before submitting**:
- ✅ All tests pass
- ✅ Code follows style guidelines
- ✅ Documentation is updated
- ✅ Commit messages are clear

**PR Description should include**:
- What changes were made
- Why the changes were necessary
- How to test the changes
- Screenshots (if UI changes)
- Related issues (if any)

**Example PR**:
```markdown
## Description
Adds support for Artillery.io JSON output format.

## Motivation
Artillery is a popular load testing tool, and users have requested support.

## Changes
- Added `ArtilleryParser` class in `heimr/parsers/artillery.py`
- Updated CLI to auto-detect Artillery format
- Added tests in `tests/test_artillery_parser.py`
- Updated README with Artillery example

## Testing
- Tested with sample Artillery output files
- All existing tests pass
- Added 5 new test cases for Artillery parser

## Related Issues
Closes #42
```

---

## Style Guidelines

### Python Code Style

We follow [PEP 8](https://pep8.org/) with some modifications:

```python
# Use Black for formatting
black heimr/

# Use flake8 for linting
flake8 heimr/

# Use type hints
def parse_file(file_path: str) -> pd.DataFrame:
    """Parse load test file and return DataFrame."""
    pass

# Docstrings for all public functions
def detect_anomalies(df: pd.DataFrame) -> List[str]:
    """
    Detect anomalies in load test data.
    
    Args:
        df: DataFrame with 'elapsed' column
        
    Returns:
        List of detected anomaly signals
    """
    pass
```

### Documentation Style

- Use Markdown for documentation
- Keep lines under 100 characters
- Use code blocks with language specification
- Include examples for all features

### Commit Message Style

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(parser): add Artillery.io support

- Implement ArtilleryParser class
- Add auto-detection for Artillery JSON format
- Update CLI to handle Artillery files

Closes #42
```

---

## Adding New Features

### Adding a New Parser

1. Create parser file in `heimr/parsers/`:
   ```python
   # heimr/parsers/artillery.py
   import pandas as pd
   
   class ArtilleryParser:
       def __init__(self, file_path: str):
           self.file_path = file_path
       
       def parse(self) -> pd.DataFrame:
           # Implementation
           pass
   ```

2. Add auto-detection in `cli.py`:
   ```python
   def detect_format(file_path):
       if file_path.endswith('.json'):
           # Check if Artillery format
           with open(file_path) as f:
               data = json.load(f)
               if 'aggregate' in data and 'scenarios' in data:
                   return 'artillery'
   ```

3. Add tests:
   ```python
   # tests/test_artillery_parser.py
   def test_artillery_parser():
       parser = ArtilleryParser('tests/fixtures/artillery.json')
       df = parser.parse()
       assert 'elapsed' in df.columns
   ```

4. Update documentation in README.md

### Adding a New Failure Scenario

1. Add a new pattern detection to `heimr/detector.py`
   

2. Update `scripts/generate_mock_data.py`:
   ```python
   elif "New Scenario" in name:
       # Generate scenario-specific pattern
       elapsed = generate_new_pattern()
   ```

3. Test with validation script

### Adding Observability Integration

1. Create client in `heimr/observability/`:
   ```python
   # heimr/observability/newrelic.py
   class NewRelicClient:
       def __init__(self, api_key: str):
           self.api_key = api_key
       
       def get_metrics(self, start_time, end_time):
           # Implementation
           pass
   ```

2. Add CLI arguments in `cli.py`

3. Update multi-signal detection to use new data

---

## Questions?

- 📧 Email: [jd.estevezcastillo@gmail.com](mailto:jd.estevezcastillo@gmail.com)
- 🐛 Issues: [GitHub Issues](https://github.com/jdestevezcastillo-perfeng/Heimr.ai/issues)

---

## License

By contributing to Heimr, you agree that your contributions will be licensed under the AGPL v3 license.

---

Thank you for contributing to Heimr! 🎉
