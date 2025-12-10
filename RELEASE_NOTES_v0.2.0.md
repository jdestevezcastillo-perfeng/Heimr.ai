# Release v0.2.0 - JVM Analysis & Chaos Testing

Released: December 10, 2025

## 🎯 Highlights

This release introduces **JVM Performance Analysis** - a major new capability that parses Thread Dumps, Heap Dumps, and GC Logs to correlate JVM behavior with load test performance issues.

## ✨ New Features

### JVM Analysis Integration
- **Thread Dump Parser** (`--jvm-thread-dump`): Analyzes jstack output for deadlocks, lock contention, and thread state distribution
- **Heap Dump Parser** (`--jvm-heap-dump`): Parses jmap histograms for memory leak detection and top memory consumers
- **GC Log Parser** (`--jvm-gc-log`): Analyzes G1/CMS/Parallel GC logs for pause times, frequency, and memory pressure

### JVM Visualizations
- **Thread State Pie Chart**: Donut chart showing RUNNABLE/BLOCKED/WAITING/TIMED_WAITING distribution with deadlock warnings
- **GC Pause Timeline**: Scatter plot of GC events over time with 200ms SLA threshold line, differentiating Young GC vs Full GC

### LLM Context Enhancement
- JVM analysis summaries are now injected into the LLM prompt for AI-powered correlation
- LLM analyzes thread contention, GC pauses, and heap pressure alongside latency spikes
- Custom prompt templates support `{jvm_context}` variable

### Demo Environment (LOCAL/chaos-test-env/)
- Spring Boot Petstore API with JVM instrumentation
- Docker Compose configuration for local testing
- Chaos generators for GC stress and DB lock contention
- K6 load test scripts with custom metrics
- Full observability stack (Prometheus, Loki, Tempo)

## 🐛 Bug Fixes

- **Fixed report overwrite bug**: Markdown report no longer overwrites HTML report when output is `.html`
- HTML reports now saved as `.html`, Markdown reports as `.md`

## 📝 CLI Changes

New CLI arguments:
```bash
heimr analyze results.json \
  --jvm-thread-dump thread_dump.txt \
  --jvm-heap-dump heap_histogram.txt \
  --jvm-gc-log gc.log \
  --output report.html
```

## 📁 Files Added

- `heimr/parsers/threaddump.py` - Thread dump parser with deadlock detection
- `heimr/parsers/heapdump.py` - Heap histogram parser with leak detection  
- `heimr/parsers/gclog.py` - GC log parser for G1/CMS/Parallel collectors
- `tests/test_jvm_parsers.py` - 14 unit tests for JVM parsers
- `tests/fixtures/sample_*.txt` - Test fixtures for all JVM data types

## 📁 Files Modified

- `heimr/cli.py` - Added JVM CLI args + JVM report section + fixed report overwrite
- `heimr/analyzer.py` - JVM parsing integration + pass-through to LLM
- `heimr/llm.py` - `_format_jvm_context()` + JVM prompt injection
- `heimr/report_charts.py` - `thread_state_pie()` + `gc_pause_timeline()` methods

## 🧪 Testing

All 14 JVM parser tests pass:
- Thread dump parsing, state detection, deadlock detection, hot locks
- Heap histogram parsing, memory leak indicators
- GC log parsing, pause analysis, timeline generation

## 📖 Example Output

When JVM data is provided, reports include:

```
## ☕ JVM Analysis

### Thread States
[Interactive pie chart with thread state distribution]

### GC Pause Timeline  
[Timeline chart with GC events and 200ms SLA line]

**GC Summary:** G1 collector, 516 events, 0.77s total pause time
```

## 🔜 Coming Soon

- JSON format support for Spring Boot Actuator thread dumps
- Flamegraph generation from thread dumps
- Memory leak trend analysis over multiple heap snapshots
