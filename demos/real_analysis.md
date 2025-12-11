# Analysis of 10-Minute Load Test (Real Run)

**Date:** 2025-12-09 22:15 CET
**Status:** ❌ FAILED

## 1. Executive Summary
Crucially, the `heimr analyze` command you ran targeted an older file (`demo-10min.json` from 20:17). The actual load test we just completed **did not pass**. It revealed significant performance degradation due to database contention.

## 2. Key Performance Indicators (From k6.log)

| Metric | Measured Value | Threshold | Status |
|--------|---------------|-----------|--------|
| **P95 Latency** | **6.93 s** | < 3.00 s | ❌ Breached |
| **Max Latency** | **16.19 s** | N/A | ⚠️ Critical |
| **Error Rate** | **2.06%** | < 10% | ✅ Passed (but non-zero) |
| **Throughput** | ~2.2 req/s | N/A | Low (throttled by DB) |

## 3. Root Cause Analysis
The application is suffering from **SQLite Concurrency Locking**.

### Evidence
1.  **High Latency Spikes (16s):** SQLite allows only one writer at a time. The test mixed `POST /api/orders` (Writes) with heavy `GET` (Reads). The writes locked the database file, causing read operations to wait (block) until the lock was released.
2.  **500 Internal Server Errors (2%):** These requests likely timed out waiting for the lock (default SQLite timeout is 5s), resulting in `OperationalError: database is locked`.
3.  **Slow Trace Example:** Trace `0046785e...` took **2.4s**, confirming even simple reads were blocked.
4.  **"Slow" Endpoint Impact:** The 10% traffic to `/api/slow` (which holds a sleep + DB connection) exacerbated the issue by keeping workers busy.

## 4. Recommendations
The current SQLite architecture is insufficient for concurrent load.
1.  **Migrate to PostgreSQL:** Use a proper client-server database with row-level locking (MVCC) to handle concurrent reads/writes.
2.  **Optimize Transactions:** Reduce the duration of write transactions.

**Conclusion:** The instrumentation successfully captured the bottleneck. This is a perfect "Incident Report" scenario.
