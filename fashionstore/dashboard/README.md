# FashionStore — Resiliency & Test Control Center

An interactive **Streamlit** dashboard for IS458 (Cloud Management and Engineering). It serves as a visual control center alongside the **AWS CloudWatch Dashboard** to trigger load tests, execute chaos drills, and inspect real-time cloud telemetry.

---

## Quick Start

From the `fashionstore/` directory:

### Option 1: Via Makefile (using `uv` or installed Python)
```bash
make dashboard
```

### Option 2: Directly via `uv` (Zero-install)
```bash
uv run --with streamlit --with boto3 --with requests streamlit run dashboard/app.py
```

### Option 3: Standard Python / venv
```bash
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```

Once launched, open `http://localhost:8501` in your browser.

---

## How It Works with AWS CloudWatch

```
Browser Tab 1: AWS CloudWatch             Browser Tab 2: Streamlit Control Center
(ap-southeast-1)                          (localhost:8501)
───────────────────────────────────       ───────────────────────────────────────
• Queue Backlog & DLQ Graphs              • [💥 Trigger Payment Outage]
• process-checkout Lambda Metrics         • [☠️ Run DLQ Redrive Drill]
• Pilot 90/10 Split Request Counts        • [⚡ Run Flash Sale (60 buyers vs 50)]
• RDS CPU Utilization & Connections       • [💀 Abrupt Pod Kill Drill]
• Real-time Alarm Status (11 Alarms)      • Live Subprocess Streaming Logs
```

During a presentation or video recording:
1. Open the **AWS CloudWatch Dashboard** on one half of your screen.
2. Open the **Streamlit Control Center** on the other half.
3. Click a failure drill (e.g. *Payment Outage* or *Flash Sale*).
4. Watch the live execution logs stream in Streamlit while the corresponding CloudWatch graphs react in real time.

---

## Features

1. **Chaos & Failure Drills**:
   * **Payment Outage**: Throttles `payment-api` Lambda to 0 concurrency, places an order, watches it stay safely pending in SQS, restores concurrency, and verifies eventual confirmation.
   * **Poison Message & DLQ Redrive**: Quarantines failed messages into `checkout-dlq` and invokes SQS redrive.
   * **Abrupt Pod Kill**: Terminates an active container pod abruptly while verifying zero 5xx errors via ALB TargetGroupBinding.
   * **SQS Partition & Reconciler**: Simulates store-api pod network partition and demonstrates the background `@Scheduled` reconciler recovering missed orders.
   * **Flash Sale Concurrency**: 60 buyers simultaneously race for 50 units of `FLASH-001`, proving zero negative inventory and exact atomic row-lock decrements.
2. **Load & Concurrency Benchmarks (k6)**:
   * **Full System Performance**: Benchmarks browse and checkout paths across CloudFront, ALB, and EKS.
   * **CloudWatch Telemetry**: Visualizes ingress traffic, p95 latency, and RDS database load in real time.
3. **Cloud Safety Telemetry & Budget**:
   * Inspects SQS queue depths, in-flight messages, and CloudWatch alarms.
   * Displays the current spend against the US$100 student alert budget from AWS Budgets.
