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
├── heimr/                  # Main package
│   ├── parsers/           # Load test result parsers
│   │   ├── jtl.py        # JMeter parser
│   │   ├── k6.py         # k6 parser
│   │   ├── gatling.py    # Gatling parser
│   │   └── locust.py     # Locust parser
│   ├── observability/     # Observability integrations
│   │   ├── prometheus.py # Prometheus client
│   │   ├── loki.py       # Loki client
│   │   └── tempo.py      # Tempo client
│   ├── detector.py        # Anomaly detection
│   ├── llm.py            # LLM integration
│   └── cli.py            # CLI interface
│   ├── llm.py            # LLM integration
│   └── cli.py            # CLI interface
├── tests/                 # Test suite
├── data/                  # Test data and mocks
├── docs/                  # Documentation
└── demos/                 # Demo scripts
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

### Testing with Mock Data

You can run the included test suite to validate changes:

```bash
# Run pytest (includes unit and integration tests)
pytest

# Validate output generation
python tests/validate_outputs.py
```

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

- 📧 Email: [dev@heimr.ai](mailto:dev@heimr.ai)
- 💬 Discord: [Join our community](https://discord.gg/heimr)
- 🐛 Issues: [GitHub Issues](https://github.com/heimr-ai/heimr/issues)

---

## License

By contributing to Heimr, you agree that your contributions will be licensed under the project's proprietary license.

---

Thank you for contributing to Heimr! 🎉
