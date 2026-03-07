# Deployment Gating

[← Back to Index](../WIKI.md)

Heimr's agent mode is an autonomous performance engineering agent that makes deployment gate decisions using a **ReAct loop** (Reason → Act → Observe).

---

## How the Agent Works

Unlike `heimr analyze` (which runs a fixed pipeline), the agent **dynamically decides** which tools to call based on what it discovers:

```
┌─────────┐     ┌─────────┐     ┌─────────┐
│  THINK  │ ──▶ │   ACT   │ ──▶ │ OBSERVE │ ──▶ (loop or finish)
│         │     │         │     │         │
│ Reason  │     │ Call a  │     │ Read    │
│ about   │     │ tool    │     │ tool    │
│ next    │     │         │     │ output  │
│ step    │     │         │     │         │
└─────────┘     └─────────┘     └─────────┘
```

The agent iterates up to `--max-iterations` times (default: 10), calling tools as needed until it reaches a verdict.

### Available Tools

The agent has 8 tools at its disposal:

| Tool | Purpose |
|------|---------|
| `parse_load_test` | Parse file, detect format, extract metadata |
| `compute_kpis` | Calculate throughput, latency percentiles, error rate, per-endpoint KPIs |
| `detect_anomalies` | Statistical anomaly detection (z-score, MAD, trend modes) |
| `query_prometheus` | Fetch system metrics (CPU, memory, disk, network) |
| `query_loki` | Fetch error/warning logs with categorization |
| `query_tempo` | Fetch slow traces above a duration threshold |
| `evaluate_gate` | Run full analysis pipeline and produce deployment verdict |
| `run_full_analysis` | One-shot complete analysis with optional LLM explanation |

---

## Basic Usage

```bash
heimr agent results.json \
  --gate-policy strict \
  --fail-condition "p99_latency > 500" \
  --fail-condition "error_rate > 1" \
  --verbose
```

### Key Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--gate-policy` | `strict` | `strict` = fail pipeline on issues; `advisory` = warn only |
| `--mode` | `autonomous` | `autonomous` = agent decides alone; `supervised` = human approval |
| `--max-iterations` | `10` | Safety limit on ReAct loop iterations |
| `--fail-condition` | — | Explicit thresholds (repeatable). Format: `metric > value` |
| `--verbose` | off | Print each reasoning step as it happens |
| `--task` | auto | Custom task description for the agent |

### Supported Fail Conditions

- `p95_latency > <ms>` — 95th percentile response time
- `p99_latency > <ms>` — 99th percentile response time
- `error_rate > <percent>` — Error percentage
- `throughput < <rps>` — Minimum requests per second

---

## Gate Policies

### Strict (default)

The agent's verdict controls the pipeline exit code:
- `APPROVE` → exit code 0 (pipeline continues)
- `REJECT` → exit code 1 (pipeline fails)

Use this for production deployment gates.

### Advisory

The agent reports findings but always exits 0:
- `APPROVE` → exit code 0
- `WARN` → exit code 0 (issues logged but pipeline continues)

Use this for staging environments or initial rollout.

---

## With Observability

Connect to your monitoring stack for multi-signal correlation:

```bash
heimr agent results.json \
  --gate-policy strict \
  --prometheus http://prometheus:9090 \
  --loki http://loki:3100 \
  --tempo http://tempo:3200 \
  --fail-condition "p99_latency > 500" \
  --verbose
```

The agent will query each source during the load test time window and correlate findings across signals.

You can also use local JSON files:

```bash
heimr agent results.json \
  --prometheus ./metrics.json \
  --loki ./logs.json \
  --tempo ./traces.json
```

---

## Audit Trail

Every agent run produces a JSON audit trail saved to `<results_file>_agent_audit.json`. It contains:

- Every reasoning step (thoughts)
- Every tool call and its arguments
- Every tool response
- Final verdict with reasoning
- Timing information

This makes every deployment decision fully traceable and auditable.

---

## CI/CD Integration

### GitHub Action

```yaml
- name: Performance Gate
  uses: jdestevezcastillo-perfeng/heimr-ai@main
  with:
    results-file: results.json
    gate-policy: strict
    fail-conditions: "p99_latency > 500, error_rate > 1"
    prometheus: http://prometheus:9090
    loki: http://loki:3100
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

**Outputs:**
| Output | Description |
|--------|-------------|
| `verdict` | `APPROVE`, `REJECT`, or `WARN` |
| `exit-code` | `0` (pass) or `1` (fail) |
| `audit-trail` | Path to the audit trail JSON |

### Docker

```bash
docker run --rm \
  -v $(pwd)/results:/data \
  juanestevezcastillo/heimr:latest \
  agent /data/results.json \
  --gate-policy strict \
  --fail-condition "p99_latency > 500"
```

### GitHub Actions Step Summary

Add `--ci-summary` to write a Markdown summary to `$GITHUB_STEP_SUMMARY`:

```bash
heimr agent results.json --gate-policy strict --ci-summary
```

### JUnit XML

Add `--junit-output` for CI test reporting:

```bash
heimr agent results.json --junit-output perf-results.xml
```

---

## Example: Verbose Agent Output

```
🤖 Heimr Agent — autonomous mode
📁 Results: results.json
🚦 Gate policy: strict
🔄 Max iterations: 10

[Iteration 1] THOUGHT: I need to start by parsing the load test file.
[Iteration 1] ACTION: parse_load_test
[Iteration 1] OBSERVATION: Parsed k6 JSON, 5000 requests, 3 endpoints...

[Iteration 2] THOUGHT: Now I should compute KPIs to understand performance.
[Iteration 2] ACTION: compute_kpis
[Iteration 2] OBSERVATION: P99=1250ms, error_rate=2.3%, throughput=167 rps...

[Iteration 3] THOUGHT: P99 exceeds 500ms threshold. Let me check anomalies.
[Iteration 3] ACTION: detect_anomalies
[Iteration 3] OBSERVATION: 12 anomalies detected, concentrated on /api/orders...

[Iteration 4] THOUGHT: I have enough evidence. Let me evaluate the gate.
[Iteration 4] ACTION: evaluate_gate
[Iteration 4] OBSERVATION: REJECT — p99_latency (1250ms) > 500ms threshold

============================================================
📋 Verdict:
REJECT: P99 latency of 1250ms exceeds the 500ms threshold.
12 anomalies detected on /api/orders endpoint.
Error rate of 2.3% exceeds 1% threshold.

⏱️  Completed in 4.2s (4 iterations)
============================================================
```

---

## Next Steps

- [MCP Integration](03-mcp-integration.md) — Use Heimr tools from Claude
- [Performance Reports](04-performance-reports.md) — Generate detailed HTML/PDF reports
- [CI/CD Integration](06-ci-cd-integration.md) — Full pipeline examples
- [Configuration](08-configuration.md) — `heimr.yaml` reference
