# CI/CD Integration

[← Back to Index](../WIKI.md)

Heimr is designed to act as an automated **Performance Gate** in your CI/CD pipelines. It provides binary Pass/Fail verdicts, rich context via tags, and standardized reporting formats to block regressions before they reach production.

---

## Installation Methods

### Docker (Recommended for CI/CD)

The Docker image is the easiest way to run Heimr in any CI/CD environment—no Python setup required.

```bash
# Pull the latest version
docker pull juanestevezcastillo/heimr:latest

# Or pin to a specific version
docker pull juanestevezcastillo/heimr:v0.1.0
```

**Image details:**
- **Repository:** `juanestevezcastillo/heimr`
- **Tags:** `latest`, `v0.1.0`
- **Architectures:** `linux/amd64`, `linux/arm64`
- **Base:** Python 3.9-slim (~200MB)

### pip install

For environments where you prefer Python packages:

```bash
# Core installation
pip install heimr-ai

# With OpenAI/Ollama LLM support
pip install heimr-ai[openai]

# With all LLM providers
pip install heimr-ai[llm]
```

---

## Docker Usage

### Basic Analysis

Mount your test results directory and run analysis:

```bash
docker run --rm \
  -v $(pwd)/results:/data \
  juanestevezcastillo/heimr:latest \
  analyze /data/results.jtl --output /data/report.md
```

### With Observability Tools

Connect to your monitoring stack for full correlation analysis:

```bash
docker run --rm \
  -v $(pwd)/results:/data \
  --network host \
  juanestevezcastillo/heimr:latest \
  analyze /data/results.jtl \
    --prometheus http://localhost:9090 \
    --loki http://localhost:3100 \
    --tempo http://localhost:3200 \
    --output /data/report.md
```

### Using Pre-exported Observability Data

If you've exported Prometheus/Loki/Tempo data as JSON files:

```bash
docker run --rm \
  -v $(pwd)/data:/data \
  juanestevezcastillo/heimr:latest \
  analyze /data/results.jtl \
    --prometheus /data/prometheus_metrics.json \
    --loki /data/loki_logs.json \
    --tempo /data/tempo_traces.json \
    --output /data/report.md
```

### With LLM Analysis (Ollama)

For AI-powered root cause analysis, connect to your Ollama instance:

```bash
docker run --rm \
  -v $(pwd)/results:/data \
  --network host \
  juanestevezcastillo/heimr:latest \
  analyze /data/results.jtl \
    --llm-url http://localhost:11434/v1 \
    --llm-model qwen3.5:9b \
    --output /data/report.md
```

---

## Performance Gating

Configure Heimr to fail the build (exit code 1) based on performance criteria.

### Static Thresholds

Fail if a specific metric exceeds a defined limit:

```bash
heimr analyze results.jtl \
  --fail-condition "p95_latency > 800" \
  --fail-condition "error_rate > 1.0"

You can also tune built-in multi-signal thresholds in `heimr.yaml`:

```yaml
cpu_threshold: 0.8
mem_growth_threshold: 0.5
anomaly_threshold: 0
error_rate_threshold: 0
```
```

**Supported Metrics:**
- `p95_latency`, `p99_latency` (milliseconds)
- `error_rate` (percentage)
- `throughput` (requests/second)

### Regression Testing

Fail if performance degrades compared to a baseline:

```bash
heimr analyze results.jtl \
  --compare-baseline previous_results.jtl \
  --fail-on-regression 10
```
*This example fails if any metric degrades by more than 10%.*

---

## Adding Context (`--tag`)

Inject metadata into the Heimr report to trace issues back to specific commits:

```bash
heimr analyze results.jtl \
  --tag "commit=${GITHUB_SHA}" \
  --tag "branch=${GITHUB_REF_NAME}" \
  --tag "build_id=${BUILD_NUMBER}"
```

---

## CI Platform Examples

### GitHub Actions

**Using Docker (Recommended):**

```yaml
name: Performance Test
on: [push]

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      # Run your load test (k6 example)
      - name: Run k6 Test
        uses: grafana/k6-action@v0.3.1
        with:
          filename: tests/load_test.js
          flags: --out json=results.json
      
      # Analyze with Heimr
      - name: Heimr Analysis
        run: |
          docker run --rm \
            -v ${{ github.workspace }}:/data \
            juanestevezcastillo/heimr:latest \
            analyze /data/results.json \
              --fail-condition "p95_latency > 500" \
              --fail-condition "error_rate > 0.1" \
              --tag "commit=${{ github.sha }}" \
              --ci-summary /data/summary.md \
              --output /data/report.md
          
          cat summary.md >> $GITHUB_STEP_SUMMARY
      
      - name: Upload Report
        uses: actions/upload-artifact@v4
        with:
          name: heimr-report
          path: report.md
```

**Using pip install:**

```yaml
- name: Install Heimr
  run: pip install heimr-ai

- name: Analyze Results
  run: |
    heimr analyze results.json \
      --fail-condition "p95_latency > 500" \
      --tag "commit=${{ github.sha }}" \
      --ci-summary $GITHUB_STEP_SUMMARY
```

### GitLab CI

```yaml
stages:
  - test
  - analyze

load_test:
  stage: test
  image: grafana/k6:latest
  script:
    - k6 run tests/load_test.js --out json=results.json
  artifacts:
    paths:
      - results.json

heimr_analysis:
  stage: analyze
  image: juanestevezcastillo/heimr:latest
  script:
    - heimr analyze results.json \
        --fail-condition "p95_latency > 500" \
        --fail-condition "error_rate > 0.1" \
        --tag "commit=${CI_COMMIT_SHA}" \
        --tag "branch=${CI_COMMIT_REF_NAME}" \
        --junit-output heimr-results.xml \
        --output report.md
  artifacts:
    reports:
      junit: heimr-results.xml
    paths:
      - report.md
  dependencies:
    - load_test
```

### Jenkins (Declarative Pipeline)

```groovy
pipeline {
    agent any
    
    stages {
        stage('Load Test') {
            steps {
                sh 'k6 run tests/load_test.js --out json=results.json'
            }
        }
        
        stage('Heimr Analysis') {
            agent {
                docker {
                    image 'juanestevezcastillo/heimr:latest'
                }
            }
            steps {
                sh '''
                    heimr analyze results.json \
                      --fail-condition "p95_latency > 500" \
                      --fail-condition "error_rate > 0.1" \
                      --tag "commit=${GIT_COMMIT}" \
                      --tag "build=${BUILD_NUMBER}" \
                      --junit-output heimr-results.xml \
                      --output report.md
                '''
            }
            post {
                always {
                    junit 'heimr-results.xml'
                    archiveArtifacts artifacts: 'report.md'
                }
            }
        }
    }
}
```

### Azure DevOps

```yaml
trigger:
  - main

pool:
  vmImage: 'ubuntu-latest'

stages:
  - stage: LoadTest
    jobs:
      - job: RunTest
        steps:
          - script: |
              curl -L https://github.com/grafana/k6/releases/download/v0.47.0/k6-v0.47.0-linux-amd64.tar.gz | tar xz
              ./k6 run tests/load_test.js --out json=results.json
            displayName: 'Run k6 Load Test'
          
          - task: Docker@2
            displayName: 'Heimr Analysis'
            inputs:
              command: run
              arguments: |
                --rm -v $(System.DefaultWorkingDirectory):/data
                juanestevezcastillo/heimr:latest
                analyze /data/results.json
                  --fail-condition "p95_latency > 500"
                  --tag "commit=$(Build.SourceVersion)"
                  --tag "build=$(Build.BuildId)"
                  --junit-output /data/heimr-results.xml
                  --output /data/report.md
          
          - task: PublishTestResults@2
            inputs:
              testResultsFormat: 'JUnit'
              testResultsFiles: 'heimr-results.xml'
          
          - publish: report.md
            artifact: heimr-report
```

---

## JUnit Integration

For CI tools that visualize test results via JUnit XML (Jenkins, GitLab, Azure DevOps):

```bash
heimr analyze results.jtl --junit-output heimr-results.xml
```

This generates a test suite where:
- **P99 Latency** becomes a test case
- **Error Rate** becomes a test case
- **Anomaly Checks** become test cases
- Any threshold failures mark test cases as "Failed"

---

## Kubernetes Integration

For teams running load tests in Kubernetes environments.

### Post-Test Analysis Job

Run Heimr as a Kubernetes Job after your load test completes:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: heimr-analysis
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: heimr
          image: juanestevezcastillo/heimr:latest
          command:
            - heimr
            - analyze
            - /data/results.jtl
            - --prometheus
            - http://prometheus.monitoring:9090
            - --loki
            - http://loki.monitoring:3100
            - --fail-condition
            - "p95_latency > 500"
            - --output
            - /data/report.md
          volumeMounts:
            - name: test-results
              mountPath: /data
      volumes:
        - name: test-results
          persistentVolumeClaim:
            claimName: load-test-results
```

### Connecting to In-Cluster Observability

When your Prometheus/Loki/Tempo are running in the same cluster:

```bash
# Use Kubernetes service DNS names
--prometheus http://prometheus.monitoring.svc.cluster.local:9090
--loki http://loki.monitoring.svc.cluster.local:3100
--tempo http://tempo.monitoring.svc.cluster.local:3200
```

---

## Quick Reference

| Use Case | Command |
|----------|---------|
| Basic analysis | `heimr analyze results.jtl` |
| With Docker | `docker run -v $(pwd):/data juanestevezcastillo/heimr analyze /data/results.jtl` |
| Fail on threshold | `--fail-condition "p95_latency > 500"` |
| Fail on regression | `--compare-baseline baseline.jtl --fail-on-regression 10` |
| Add metadata | `--tag "commit=${GIT_SHA}"` |
| JUnit output | `--junit-output results.xml` |
| GitHub summary | `--ci-summary $GITHUB_STEP_SUMMARY` |

Notes:
- `--ci-summary` works even without `--output`; if reports are generated, artifact paths are listed.
