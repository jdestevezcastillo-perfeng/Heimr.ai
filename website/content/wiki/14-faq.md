# Frequently Asked Questions (FAQ)

## What does Heimr do?

Heimr is an automated gate for your CI/CD pipeline that says "yes, deploy this" or "no, this version will cause problems."

Just like you have gates that check "did the tests pass?" and "did the security scan pass?", Heimr is the gate that checks "does this code perform okay under load?"

**The problem it solves**: Right now, someone (or a dashboard) has to manually check load test results and decide if a build is safe to deploy. Heimr automates that decision and catches performance regressions *before* they hit production.

**How it works** (in 30 seconds):
1. Your load test runs (k6, JMeter, whatever you use)
2. You pass the results to Heimr
3. Heimr analyzes them against your thresholds ("p99 latency can't exceed 500ms", "error rate can't exceed 1%")
4. Heimr says `APPROVE` or `REJECT` with reasoning
5. Your pipeline either continues or stops

---

## How do I install it?

**Option 1: Simple (Recommended)**
```bash
pip install heimr-ai
```

That's it. It's a Python package. Requires Python 3.8+.

**Option 2: Docker**
```bash
docker run jdestevezcastillo-perfeng/heimr-ai:latest agent results.json --gate-policy strict
```

**Option 3: In your GitHub Actions** (if you use GitHub)
```yaml
- uses: jdestevezcastillo-perfeng/heimr-ai@main
```

See the [Quick Start Guide](01-quickstart.md) for detailed setup instructions.

---

## How do I set it up?

Minimal setup:
```bash
heimr agent results.json \
  --fail-condition "p99_latency > 500" \
  --fail-condition "error_rate > 1"
```

That's it. One command, two thresholds.

**If you want to use cloud LLMs** (OpenAI, Claude) for smarter analysis:
```bash
export OPENAI_API_KEY=sk-...
heimr agent results.json --fail-condition "p99_latency > 500"
```

**If you want local AI** (recommended, no data leaves your network):
```bash
# Install Ollama: https://ollama.com
ollama pull qwen3.5:9b

# Then Heimr uses it automatically
heimr agent results.json --fail-condition "p99_latency > 500"
```

See the [Configuration Guide](08-configuration.md) for advanced settings.

---

## Who makes the performance tests?

**Your team does.**

Heimr doesn't create tests — it analyzes tests that already exist. You or your QA team writes them using:
- **k6** (JavaScript, modern, recommended for DevOps)
- **JMeter** (if you already use it)
- **Gatling, Locust, or HAR files** (browser recordings)

**Typical workflow**:
```
Developer writes code
  → QA/DevOps runs load test (k6 script)
  → Test produces JSON results
  → Heimr analyzes those results
  → Pipeline approves or rejects deployment
```

**If you don't have load tests yet**, k6 is the easiest to start with:

```bash
# Install k6
brew install k6  # or apt-get, or docker

# Write a simple test (looks like JavaScript)
cat > load-test.js << 'EOF'
import http from 'k6/http';
import { check } from 'k6';

export let options = {
  vus: 100,        // 100 concurrent users
  duration: '30s', // for 30 seconds
};

export default function() {
  let res = http.get('https://your-app.example.com');
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
}
EOF

# Run it
k6 run load-test.js --out json=results.json

# Pass results to Heimr
heimr agent results.json --fail-condition "error_rate > 1"
```

---

## What hardware does it need to run?

**Heimr itself is lightweight**:
- **CPU**: Basically any CPU (not compute-intensive)
- **Memory**: 256 MB minimum, 512 MB recommended
- **Disk**: < 100 MB

**The bottleneck is your LLM choice**:

| Setup | Hardware | Cost | Latency |
|-------|----------|------|---------|
| Local Ollama (Qwen 3.5) | 4GB RAM, any CPU | Free | 5-10s per analysis |
| OpenAI API | None (runs in cloud) | ~$0.01-0.10 per analysis | 2-3s |
| Anthropic Claude API | None (runs in cloud) | ~$0.05-0.20 per analysis | 2-3s |

**Most DevOps setups**: Local Ollama on the same machine or a sidecar pod.

---

## Can I run it in OpenShift/Kubernetes?

**Yes, absolutely.** Two approaches:

### Approach 1: As a Job (Simplest)
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: heimr-gate
spec:
  template:
    spec:
      containers:
      - name: heimr
        image: python:3.11-slim
        command:
        - /bin/sh
        - -c
        - |
          pip install heimr-ai
          heimr agent /results/results.json \
            --fail-condition "p99_latency > 500" \
            --fail-condition "error_rate > 1"
        volumeMounts:
        - name: results
          mountPath: /results
      volumes:
      - name: results
        configMap:
          name: load-test-results
      restartPolicy: Never
```

### Approach 2: With Local Ollama (Better)
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: heimr-with-ollama
spec:
  containers:
  # Ollama sidecar
  - name: ollama
    image: ollama/ollama:latest
    resources:
      requests:
        memory: "4Gi"
        cpu: "2"
    volumeMounts:
    - name: ollama-data
      mountPath: /root/.ollama

  # Heimr gate
  - name: heimr
    image: python:3.11-slim
    command:
    - /bin/sh
    - -c
    - |
      pip install heimr-ai
      # Wait for Ollama to start
      sleep 10
      # Pull model
      curl http://localhost:11434/api/pull -d '{"name": "qwen3.5:9b"}'
      # Run analysis
      OLLAMA_HOST=http://localhost:11434 \
      heimr agent /results/results.json \
        --fail-condition "p99_latency > 500"
    volumeMounts:
    - name: results
      mountPath: /results
    env:
    - name: OLLAMA_HOST
      value: http://localhost:11434

  volumes:
  - name: results
    configMap:
      name: load-test-results
  - name: ollama-data
    emptyDir: {}
```

**For Tekton/ArgoCD pipelines**, just use the Job approach above in your CI step.

See the [CI/CD Integration Guide](06-ci-cd-integration.md) for more pipeline examples.

---

## What's the typical DevOps setup?

```
Your laptop/CI server
├── Load test runs (k6/JMeter) → results.json
├── Heimr analyzes it (runs in container or locally)
├── If approved: pipeline continues to deploy
└── If rejected: pipeline stops, logs reason to Slack
```

**That's the whole flow.** No special infrastructure, no ML ops complexity.

---

## Does my data leave my infrastructure?

**By default, no.** If you use local Ollama (recommended), all analysis happens on your own machines. Your load test results never leave your network.

**If you use cloud LLMs** (OpenAI, Anthropic Claude), only the analyzed metrics and summary statistics are sent to the API — not your raw data. You control which LLM provider you use via configuration.

See the [AI Analysis Engine](09-ai-analysis-engine.md) documentation for details on LLM providers.

---

## What if I already have performance tests but don't know how to interpret them?

**That's exactly what Heimr is for.**

You don't need to be a performance engineer to use Heimr. Just set simple thresholds like:
- "Error rate can't exceed 1%"
- "P99 latency can't exceed 500ms"
- "Throughput must be at least 1000 requests/sec"

Heimr will:
1. Check if your test results violate these thresholds
2. Correlate with observability data (Prometheus, Loki, Tempo) if you have them
3. Provide reasoning in plain English
4. Give you an APPROVE or REJECT decision

The [Deployment Gating](02-deployment-gating.md) guide shows examples of different gate policies and fail conditions.

---

## Can Heimr work without observability tools (Prometheus, Loki, etc.)?

**Yes.** Heimr can analyze load test results standalone without any observability integrations.

However, having observability sources (Prometheus for metrics, Loki for logs, Tempo for traces) makes the analysis **much better** because Heimr can:
- Correlate performance issues with infrastructure metrics (CPU, memory, disk)
- Find error logs that explain why requests failed
- Trace slow requests to find bottlenecks

**But it's optional.** Start simple with just load test results, add observability later when you're ready.

---

## What load testing tools does Heimr support?

Heimr supports results from:
- **k6** (JSON output)
- **JMeter** (JTL/CSV files)
- **Gatling** (simulation.log)
- **Locust** (stats CSV)
- **HAR files** (browser recordings from Chrome/Firefox DevTools)

See the [Quick Start Guide](01-quickstart.md#supported-formats) for format details.

---

## How much does it cost to run Heimr?

**Heimr itself is free and open source** (AGPL v3).

**LLM costs**:
- **Local Ollama** (recommended): Free, runs on your hardware
- **OpenAI GPT-4**: ~$0.01-0.10 per analysis
- **Anthropic Claude**: ~$0.05-0.20 per analysis

Most teams use local Ollama for CI/CD pipelines to avoid per-analysis costs.

---

## Can I use Heimr in my commercial SaaS product?

Heimr is licensed under **AGPL v3**, which requires you to share your source code if you run Heimr as a network service.

**For commercial use cases** (SaaS, proprietary integrations, closed-source redistribution), contact [jd.estevezcastillo@gmail.com](mailto:jd.estevezcastillo@gmail.com) for a commercial license.

See the [README](../README.md#license) for license details.

---

## How do I get help or report bugs?

- **Documentation**: See the [Quick Start](01-quickstart.md) and [Troubleshooting](12-troubleshooting.md) guides
- **GitHub Issues**: [Report bugs or request features](https://github.com/jdestevezcastillo-perfeng/Heimr.ai/issues)
- **Email**: [jd.estevezcastillo@gmail.com](mailto:jd.estevezcastillo@gmail.com)

---

## Can I contribute to Heimr?

Yes! See the [Contributing Guide](contributing.md) and [Development Guide](13-development.md) for details on how to contribute code, documentation, or new features.
