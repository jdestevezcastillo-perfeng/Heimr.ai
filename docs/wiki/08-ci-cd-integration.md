# CI/CD Integration

[← Back to Index](../WIKI.md)

Heimr is designed to act as an automated "Performance Gate" in your CI/CD pipelines (GitHub Actions, Jenkins, GitLab CI). It provides binary Pass/Fail verdicts, rich context via tags, and standardized reporting formats to block regressions before they reach production.

## 1. Performance Gating

You can configure Heimr to fail the build (exit code 1) based on specific performance criteria or regression checks.

### Static Thresholds
Fail if a specific metric exceeds a defined limit.

```bash
heimr analyze results.jtl \
  --fail-condition "p95_latency > 800" \
  --fail-condition "error_rate > 1.0"
```

**Supported Metrics:**
- `p95_latency`, `p99_latency`
- `error_rate`
- `throughput`

### Regression Testing
Fail if performance degrades significantly compared to a baseline.

```bash
heimr analyze results.jtl \
  --compare-baseline previous_results.jtl \
  --fail-on-regression 10
```
*This example fails if any metric degrades by more than 10%.*

## 2. Adding Context (`--tag`)

In a CI environment, you want to know *exactly* which commit caused a performance drop. Use `--tag` to inject metadata into the Heimr report header.

```bash
heimr analyze results.jtl \
  --tag "commit=${GITHUB_SHA}" \
  --tag "branch=${GITHUB_REF_NAME}" \
  --tag "deploy_id=${DEPLOYMENT_ID}"
```

## 3. GitHub Actions Integration

Heimr supports generating a summary specifically formatted for the `$GITHUB_STEP_SUMMARY` environment variable, allowing you to see results directly in the Actions UI.

```yaml
- name: Heimr Performance Analysis
  run: |
    heimr analyze results.json \
      --ci-summary $GITHUB_STEP_SUMMARY \
      --output report.md
```

## 4. JUnit Integration (Jenkins/GitLab)

For tools that visualize test results via JUnit XML (like Jenkins "Test Results" tab or GitLab CI), use `--junit-output`.

```bash
heimr analyze results.jtl \
  --junit-output heimr-results.xml
```

This generates a test suite where:
- **P99 Latency** becomes a test case.
- **Error Rate** becomes a test case.
- **Anomaly Checks** become test cases.
- Any failures in thresholds mark the test cases as "Failed".

## Example Workflow (GitHub Actions)

```yaml
name: Load Test & Analyze
on: [push]

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      # ... (Run your k6/JMeter test here) ...

      - name: Install Heimr
        run: pip install heimr

      - name: Analyze Results
        run: |
          heimr analyze output.json \
            --fail-condition "p95_latency > 500" \
            --fail-condition "error_rate > 0.1" \
            --tag "commit=${{ github.sha }}" \
            --ci-summary $GITHUB_STEP_SUMMARY
```
