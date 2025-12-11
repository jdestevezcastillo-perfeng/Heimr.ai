# Configuration

[← Back to Index](../WIKI.md)

Heimr looks for a configuration file only when specified via `--config`. CLI arguments always take precedence over configuration file values.

## Example `heimr.yaml`

```yaml
# ============================================================================
# Observability Sources
# ============================================================================
# Heimr can fetch data from live URLs OR read from local JSON files.
# It automatically detects if the value is a URL (starts with http) or a file path.

# Prometheus (Metrics)
prometheus: http://localhost:9090   # Default Prometheus URL
# prometheus: ./data/metrics.json     # Or local file

# Loki (Logs)
loki: http://localhost:3100          # Default Loki URL
# loki: ./data/logs.json               # Or local file

# Tempo (Traces)
tempo: http://localhost:3200          # Default Tempo URL
# tempo: ./data/traces.json            # Or local file

# ============================================================================
# AI Analysis
# ============================================================================
# Heimr supports both local (Ollama) and cloud (OpenAI, Anthropic) models.

# 1. Local LLM (Ollama) - Recommended for Privacy
# ----------------------------------------------------------------------------
llm_url: http://localhost:11434/v1  # Default Ollama API URL
llm_model: llama3.1:8b              # Default model (Medium)

# Optional LLM reliability settings
# llm_timeout_sec: 60
# llm_max_retries: 2

# Model Options (Pull these via 'ollama pull <model>'):
# - Small:  llama3.2:3b   (~2GB VRAM)  - Good for laptops, CI/CD
# - Medium: llama3.1:8b   (~5GB VRAM)  - Best balance of speed/quality [DEFAULT]
# - Large:  qwen2.5:14b   (~9GB VRAM)  - High quality reasoning (fits on 12GB GPU)

# 2. Cloud LLMs (OpenAI / Anthropic)
# ----------------------------------------------------------------------------
# To use cloud models, DO NOT set llm_url (leave it commented or empty).
# Instead, set the following environment variables:
#   export OPENAI_API_KEY="sk-..."      -> uses gpt-5.1 by default
#   export ANTHROPIC_API_KEY="sk-..."   -> uses claude-opus-4.5 by default
#
# You can override the specific cloud model name using llm_model:
# llm_model: gpt-4-turbo

# ============================================================================
# Failure Thresholds (Optional)
# ============================================================================
#
# These thresholds influence Heimr's built-in multi-signal verdict.
# You can also use CLI `--fail-condition` for explicit gating.
#
# anomaly_threshold: 0           # Fail if anomalies > this count
# error_rate_threshold: 0        # Fail if error_rate (%) > this value
# cpu_threshold: 0.8             # Fail if avg CPU > 80%
# mem_growth_threshold: 0.5      # Fail if memory grows > 50% during test

# ============================================================================
# Reporting
# ============================================================================
output: ./reports/analysis.md
```
