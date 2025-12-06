# Troubleshooting

[← Back to Index](../WIKI.md)

Common issues and their solutions.

---

## LLM & AI Issues

### "LLM connection failed"

**Symptoms**: Analysis fails with connection errors to the LLM.

**Solutions**:
1. Verify Ollama is running:
   ```bash
   curl http://localhost:11434
   # Should return: "Ollama is running"
   ```
2. Check if the model is pulled:
   ```bash
   ollama list
   # Should show llama3.1:8b or your configured model
   ```
3. Pull the model if missing:
   ```bash
   ollama pull llama3.1:8b
   ```

### "Model not found" or slow response

**Symptoms**: Ollama returns 404 or takes forever.

**Solutions**:
1. Ensure the model name matches exactly (including tag):
   ```bash
   # Correct
   --llm-model llama3.1:8b
   
   # Wrong (missing tag)
   --llm-model llama3.1
   ```
2. For slow responses, check system resources:
   ```bash
   # Check GPU utilization (if using GPU)
   nvidia-smi
   
   # Check RAM usage
   free -h
   ```

### Cloud API Key Issues

**Symptoms**: OpenAI/Anthropic returns 401 or "Invalid API key".

**Solutions**:
1. Verify the environment variable is set:
   ```bash
   echo $OPENAI_API_KEY
   # or
   echo $ANTHROPIC_API_KEY
   ```
2. Ensure no extra whitespace in the key.
3. Check API quota/billing on your provider dashboard.

---

## Observability Connection Issues

### "Failed to connect to Prometheus/Loki/Tempo"

**Symptoms**: Timeout or connection refused errors.

**Solutions**:
1. Verify the service is running:
   ```bash
   curl http://localhost:9090/-/healthy  # Prometheus
   curl http://localhost:3100/ready      # Loki
   curl http://localhost:3200/ready      # Tempo
   ```
2. Check firewall/network settings if connecting to remote hosts.
3. Use local file fallback if the service is unavailable:
   ```bash
   --prometheus ./exported_metrics.json
   ```

### "No metrics/logs/traces found for time range"

**Symptoms**: Analysis completes but says "No data available".

**Solutions**:
1. **Time sync is critical!** Ensure your load test machine and observability stack are synchronized (NTP).
2. Verify the test time range overlaps with available data:
   ```bash
   # Check Prometheus data range
   curl 'http://localhost:9090/api/v1/query?query=up'
   ```
3. Extend the query window if needed (Heimr auto-detects from test file).

---

## Memory & Performance Issues

### Ollama OOM (Out of Memory)

**Symptoms**: `CUDA out of memory` or system freezes during analysis.

**Solutions**:
1. Use a smaller model:
   ```bash
   --llm-model llama3.2:3b  # Only needs 4GB VRAM
   ```
2. Close other GPU-intensive applications.
3. Run on CPU (slower but works):
   ```bash
   # Ollama will auto-fallback to CPU if no GPU
   ```
4. Increase system swap:
   ```bash
   sudo fallocate -l 16G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

### Analysis takes too long

**Symptoms**: Analysis hangs or takes >10 minutes.

**Solutions**:
1. Use `--no-llm` for faster stats-only reports:
   ```bash
   heimr analyze results.jtl --no-llm
   ```
2. Reduce observability data by filtering time range.
3. Use a smaller model (`llama3.2:3b`).

---

## Parser & File Format Issues

### "Parser error" or "Unsupported file format"

**Symptoms**: Heimr can't read the input file.

**Solutions by tool**:

| Tool | Required Format | Command to Generate |
|------|-----------------|---------------------|
| **JMeter** | `.jtl` (CSV) | Default output |
| **k6** | `.json` | `k6 run --out json=results.json script.js` |
| **Gatling** | `.log` | Found in `results/` folder |
| **Locust** | `*_stats_history.csv` | Enable CSV reporting in UI or `--csv` flag |
| **HAR** | `.har` | Export from browser DevTools → Network → "Save all as HAR" |

### "No anomalies detected"

**Symptoms**: Report shows no issues, but you expected some.

**Solutions**:
1. Ensure test duration is sufficient (>1 minute recommended).
2. Check if the test actually generated varied load (not flat-line).
3. Verify timestamps in the file are correct.
4. Lower detection thresholds (advanced: modify detector config).

---

## CI/CD Issues

### Exit code not reflecting failures

**Symptoms**: Pipeline passes even though report shows issues.

**Solutions**:
1. Use explicit fail conditions:
   ```bash
   heimr analyze results.jtl \
     --fail-condition "p99_latency > 500" \
     --fail-condition "error_rate > 1.0"
   ```
2. Check that Heimr is the last command in the pipeline step.

### GitHub Step Summary not showing

**Symptoms**: `$GITHUB_STEP_SUMMARY` is empty.

**Solutions**:
1. Pass the path correctly:
   ```yaml
   - run: heimr analyze results.json --ci-summary $GITHUB_STEP_SUMMARY
   ```
2. Ensure the step has write permissions.

---

## Still Stuck?

1. Run with verbose output (if available).
2. Check the [GitHub Issues](https://github.com/heimr-ai/heimr/issues) for similar problems.
3. Open a new issue with:
   - Heimr version (`pip show heimr-ai`)
   - Full error message
   - Sample command used
