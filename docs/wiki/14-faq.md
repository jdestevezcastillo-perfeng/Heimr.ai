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

## I don't have tests, docs, NFRs, or technical knowledge. Can Heimr still help me?

**YES — This is the vision for Heimr Autonomous Mode** (requested feature).

### The Problem

You just "vibe-coded" a Pokemon card shop. You have:
- ❌ No performance tests
- ❌ No documentation (no SAD, no API specs, no Swagger)
- ❌ No NFRs (no idea what "good" latency is)
- ❌ No technical expertise

You just want to know: **"Will my site crash when I launch?"**

### The Solution (Future Feature)

**One command**:
```bash
heimr autonomous https://mypokemonshop.com
```

**What happens** (fully autonomous):
1. **Discovers your site** (crawls with headless browser, records user flows)
2. **Understands what it does** (AI figures out "this is an e-commerce site")
3. **Generates realistic tests** (creates k6 scripts from recorded flows)
4. **Runs the tests** (simulates 50 concurrent users)
5. **Assesses performance** (no NFRs needed, uses baseline mode)
6. **Reports in plain English** (no jargon, actionable recommendations)

**Output (if everything is fine)**:
```
✅ Your site is ready to handle traffic!

Performance Summary:
  ✅ Browse products: Fast (avg 950ms)
  ✅ Search: Instant (avg 145ms)
  ✅ Checkout: Good (avg 2.3s)

Your site is faster than 75% of e-commerce sites.
Predicted cart abandonment: ~4% (excellent)

🎉 You're good to launch!
```

**Output (if there's a problem)**:
```
🔴 Issues detected — Fix before launch

What's Wrong (Plain English):
  1. 🔴 CRITICAL: Add to cart is broken
     - 15% of requests fail with error 500
     - Problem: No inventory check for out-of-stock items
     - Impact: Users can't buy products, will leave
     - Fix: Add inventory validation
     - Estimated effort: 2 hours

  2. 🔴 CRITICAL: Checkout is too slow (4.8s avg)
     - Problem: Stripe payment API calls are slow
     - Impact: 12% of users will abandon cart
     - Fix: Process payments asynchronously
     - Estimated effort: 4 hours

Want AI to suggest code fixes? (y/n)
```

### Current Status

This feature is **not yet implemented** but is the long-term vision for Heimr.

**GitHub Issue**: [#19 - Fully Autonomous Performance Testing](https://github.com/jdestevezcastillo-perfeng/Heimr.ai/issues/19)

This combines:
- [Issue #17](https://github.com/jdestevezcastillo-perfeng/Heimr.ai/issues/17) - Test generation from documentation
- [Issue #18](https://github.com/jdestevezcastillo-perfeng/Heimr.ai/issues/18) - Assessment without NFRs
- NEW: Website discovery via crawling
- NEW: Plain English reporting for non-technical users

👍 the issue if you want this feature!

### Why This Matters

**Heimr's mission**: Make performance testing accessible to everyone.

Right now, performance testing requires:
- Technical expertise
- Time to write tests
- Knowledge to interpret results

**Autonomous mode removes all barriers** — just provide a URL, get plain English recommendations.

**Target users**:
- Indie hackers who built their own site
- Non-technical founders
- Small business owners
- Anyone who just wants to know "is my site okay?"

**For commercial development** or early access to Autonomous mode:
- Contact: jd.estevezcastillo@gmail.com

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

## Can Heimr generate performance tests for me, or does it only analyze existing tests?

**Current Heimr (v0.2)**: Only analyzes existing tests. You need to create the load tests yourself (using k6, JMeter, etc.).

**Future feature (requested)**: A **Performance Test Generator Agent** that autonomously creates tests for you.

### What the Test Generator Agent would do:

1. **Read your documentation** (Software Architecture Document, OpenAPI specs, NFRs)
2. **Extract requirements** (latency thresholds, throughput targets)
3. **Generate test plan** (which endpoints to test, load profiles)
4. **Write test scripts** (k6, JMeter)
5. **Execute tests** against your environment
6. **Analyze results** (using existing Heimr agent)
7. **Iterate and refine** until tests are validated

### What you'd need to provide (minimum):

```yaml
# Example config
documentation:
  - "./docs/architecture.md"       # Your system architecture
  - "./docs/api-spec.yaml"         # OpenAPI/Swagger spec
  - "./docs/nfrs.md"               # Non-functional requirements

environment:
  base_url: "https://staging.myapp.com"
  auth:
    type: "bearer"
    credentials_env: "TEST_API_KEY"

requirements:
  - metric: "p99_latency"
    threshold: "< 500ms"
  - metric: "error_rate"
    threshold: "< 1%"
```

That's it! The agent would handle the rest.

### Current status:

This feature is **not yet implemented** but has been requested by the community. Track progress here:

**GitHub Issue**: [#17 - Performance Test Generator Agent](https://github.com/jdestevezcastillo-perfeng/Heimr.ai/issues/17)

👍 the issue if you want this feature, or comment with your use case.

**For commercial development** (priority implementation for your team):
- Contact: jd.estevezcastillo@gmail.com

---

## What if we don't have NFRs? How do we know if our performance is "good"?

**This is very common** — most startups and small teams don't have formal NFRs (Non-Functional Requirements).

**Good news**: You don't need predefined thresholds. Heimr can assess performance in multiple ways:

### Option 1: Use Industry Benchmarks (Easiest)

Use research-backed standards for your application type:

**General Web APIs**:
- p99 latency < 500ms
- Error rate < 1%

**E-commerce**:
- Product page < 2s
- Checkout flow < 3s
- Search < 200ms

**Real-time apps** (chat, gaming):
- p99 latency < 100ms

**Research-backed facts**:
- Google: 53% of users abandon sites that take >3s to load
- Amazon: 100ms latency = 1% revenue loss
- Users perceive <100ms as "instant", >1s as "slow"

**Future Heimr** (requested feature):
```bash
heimr agent results.json --preset web-api
# Automatically uses industry-standard thresholds
```

### Option 2: Baseline Mode (Recommended)

Establish a baseline from your first test, then prevent regressions:

**First run** (establish baseline):
```bash
heimr agent results.json --mode baseline --save-baseline baseline.json
```

Output: "Your current p99 is 320ms, error rate is 0.3%"

**Subsequent runs** (compare to baseline):
```bash
heimr agent new-results.json \
  --compare-to-baseline baseline.json \
  --max-regression 20%
```

Output: "REJECT: p99 increased by 40% (from 320ms to 450ms)"

**This is the best approach** — you're not saying "500ms is good", you're saying "don't get 20% worse than what we have now."

### Option 3: Comparative Mode (CI/CD)

Compare each build against the **previous build**:

```bash
heimr agent current-build.json \
  --compare-to previous-build.json \
  --max-regression 15%
```

Logic: If latency increases >15% or throughput decreases >10% → REJECT

### Option 4: Auto-Discovery from Production (Advanced)

Query your production Prometheus metrics to learn "normal" performance:

```bash
heimr agent test-results.json \
  --discover-thresholds \
  --prometheus http://prometheus:9090 \
  --time-range 7d \
  --tolerance 20%
```

Heimr will:
1. Query production metrics for last 7 days
2. Calculate baseline (e.g., p99=280ms in prod)
3. Set test thresholds at +20% tolerance (p99<336ms)
4. Fail if test exceeds production by >20%

### Option 5: User Impact Mode

Translate technical metrics into **business impact**:

```bash
heimr agent results.json \
  --user-impact-mode \
  --acceptable-abandonment-rate 5%
```

Heimr calculates:
- Your p99: 4.2s
- **Predicted abandonment rate**: 9.8% (based on Google research)
- **Verdict**: REJECT (exceeds 5% threshold)

### Recommendation for Your Startup

**Start simple with baseline mode**:

1. Run your first load test
2. Establish baseline: `heimr agent results.json --mode baseline --save-baseline baseline.json`
3. In CI/CD, compare to baseline: `heimr agent new-results.json --compare-to-baseline baseline.json --max-regression 20%`

**No NFRs needed.** Just "don't get 20% worse than the first run."

### Current Status

These modes are **not yet implemented** but have been requested by the community:

**GitHub Issue**: [#18 - Performance Assessment Without Predefined NFRs](https://github.com/jdestevezcastillo-perfeng/Heimr.ai/issues/18)

👍 the issue if you want this feature, or comment with your use case.

**For commercial development** (priority implementation):
- Contact: jd.estevezcastillo@gmail.com

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
