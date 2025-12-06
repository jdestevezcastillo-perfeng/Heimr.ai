# HAR Recording Guide for Heimr Demo

This guide explains how to record browser sessions as HAR files for analysis with Heimr.

## What is HAR?

HAR (HTTP Archive) is a JSON format that captures all HTTP traffic from a browser session, including:
- Request/response timing breakdowns (DNS, TCP, SSL, wait, receive)
- Status codes and error responses
- Request/response sizes
- Full waterfall data

## Recording Steps

### Option 1: Chrome DevTools

1. **Open Chrome DevTools**: Press `F12` or `Ctrl+Shift+I`
2. **Go to Network tab**: Click the "Network" tab
3. **Enable recording**: Ensure the red record button is active
4. **Navigate to the demo frontend**: `http://localhost:30080`
5. **Perform actions**: Click buttons, create orders, etc.
6. **Export HAR**: Right-click in the request list → "Save all as HAR with content"
7. **Save file**: Name it `demo_session.har`

### Option 2: Firefox DevTools

1. **Open DevTools**: Press `F12`
2. **Go to Network tab**
3. **Perform actions on the page**
4. **Export**: Right-click → "Save All As HAR"

### Option 3: Playwright (Automated)

```javascript
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    recordHar: { path: 'demo_session.har' }
  });
  
  const page = await context.newPage();
  await page.goto('http://localhost:30080');
  
  // Perform actions
  await page.click('button:has-text("Get Users")');
  await page.click('button:has-text("Create Order")');
  await page.click('button:has-text("Slow Endpoint")');
  
  await context.close(); // Saves HAR
  await browser.close();
})();
```

## Analyzing with Heimr

Once you have a HAR file:

```bash
# Basic analysis
heimr analyze demo_session.har

# With AI explanation
heimr analyze demo_session.har --explain

# Save report
heimr analyze demo_session.har --explain --output har_report.md
```

## Example Output

```
Analyzing demo_session.har (har)...
==================================================
HEIMR REPORT (Level 1)
==================================================
Metric                    | Value          
-------------------------------------------
Result                    | PENDING
Duration                  | 8.50 s
Requests                  | 5
Throughput                | 0.59 req/s
Error Rate                | 20.00%
Latency P50               | 156.30 ms
Latency P95               | 3545.50 ms
Latency P99               | 4893.14 ms
-------------------------------------------
```

## Tips for Good HAR Recordings

1. **Clear cache first**: Ensures all resources are fetched fresh
2. **Disable extensions**: Browser extensions can add noise
3. **Use incognito**: Avoids cached credentials/cookies
4. **Wait for loads**: Ensure pages fully load before clicking
5. **Include errors**: Hit error endpoints to test error handling analysis

## HAR File Structure

```json
{
  "log": {
    "version": "1.2",
    "creator": { "name": "Chrome DevTools" },
    "entries": [
      {
        "startedDateTime": "2025-12-06T10:00:00.000Z",
        "time": 245.5,
        "request": {
          "method": "GET",
          "url": "http://localhost:30808/api/users"
        },
        "response": {
          "status": 200,
          "content": { "size": 1250 }
        },
        "timings": {
          "dns": 12.3,
          "connect": 45.2,
          "wait": 165.4,
          "receive": 21.3
        }
      }
    ]
  }
}
```

## Comparison: HAR vs Load Test Results

| Aspect | HAR | k6/JMeter |
|--------|-----|-----------|
| **Source** | Real browser | Synthetic load |
| **VUs** | 1 (single session) | Many concurrent |
| **Timing** | Client-side (includes browser) | Server-side |
| **Use Case** | Debug, RUM | Capacity testing |
