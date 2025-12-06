# AI Analysis Engine

[← Back to Index](../WIKI.md)

Heimr's AI analysis engine is designed to act as an automated Senior Performance Engineer. It is not just a chatbot wrappers; it uses a sophisticated **Context Stuffing** architecture to provide deterministic, evidence-based Root Cause Analysis (RCA).

## Technical Architecture

The analysis pipeline operates in four distinct stages:

### 1. Multi-Modal Signal Aggregation

Before the LLM is even invoked, Heimr aggregates data from three distinct observability pillars into a unified context window:

| Signal Source | Data Type | Pre-processing Strategy |
| :--- | :--- | :--- |
| **Prometheus** | Time-series Metrics | Statistical summarization (Min, Max, Avg) per pod. calculation of trend vectors (↑/↓) to detect degradation over time. |
| **Loki** | Unstructured Logs | Log pattern recognition. Categorizes logs filter out noise (Info/Debug), and extracts error samples with their associated stack traces. |
| **Tempo** | Distributed Traces | Latency-based sampling. Extracts the "Critical Path" of the slowest requests, identifying specific span durations and operation names including DB queries. |

### 2. Context Stuffing & Serialization

Unlike RAG (Retrieval-Augmented Generation) which relies on retrieving small relevant snippets, **Context Stuffing** involves fitting the entire relevant dataset directly into the LLM's context window. Heimr leverages this by serializing the entire high-fidelity signal state into a structured prompt schema. This ensures the LLM has *global visibility* over the test run, allowing it to correlate a CPU spike in Prometheus directly with a slow DB span in Tempo and an error log in Loki.

### 3. Strict Schema Enforcement

To prevent "hallucinations"
 and ensure actionable output, the LLM is prompted with a strict role implementation:

- **Role**: Senior Performance Engineer
- **Input**: Structured JSON-like context of the test execution.
- **Output Constraint**: Strict Markdown format with required sections (Executive Summary, KPI Table, Technical Analysis).

## Model Tiers & Hardware Requirements

Heimr supports a tiered model strategy
 to balance quality, speed, and hardware constraints.

### Local Models (Privacy-First)

Run completely offline using Ollama
. No data leaves your infrastructure.

| Tier | Model | Min. GPU VRAM | Min. System RAM (CPU-only) | Use Case | Analysis Capability |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Small** | `llama3.2:3b` | **4 GB** | **8 GB** | CI/CD pipelines, Laptops | Basic anomaly flagging. Can identify obvious errors but struggles with complex correlation. |
| **Medium** | `llama3.1:8b` | **6 GB** | **16 GB** | Standard Workstations | **Default Recommended**. Great balance. capable of correlating metrics and logs effectively. |
| **Large** | `qwen2.5:14b` | **12 GB** | **32 GB** | Dedicated GPU Servers | **Deepest Reasoning**. Best at following complex instructions and correlating subtle multi-service cascading failures. |
| **Custom** | *User Defined* | *Variable* | *Variable* | Specialized / Research | **Flexible**. Connect any OpenAI-compatible API (vLLM, LM Studio) by setting `llm_url` and `llm_model`. |

### Cloud Provider Integration

For teams without GPU infrastructure
, Heimr integrates with top-tier cloud models:

- **OpenAI**: Defaults to `gpt-5.1`. Set `OPENAI_API_KEY`.
- **Anthropic**: Defaults to `claude-opus-4.5`. Set `ANTHROPIC_API_KEY`.

> [!TIP]
> **Recommendation**: Start with the **Medium** local model (`llama3.1:8b`). If you find the analysis lacks depth or misses subtle correlations, switch to **Large** (`qwen2.5:14b`) if your hardware permits, or use `claude-opus-4.5` for state-of-the-art reasoning.
