# FashionStore — Resiliency & Test Control Center

An interactive **Streamlit** dashboard for IS458 (Cloud Management and Engineering). It serves as a visual control center alongside the **AWS CloudWatch Dashboard** to trigger load tests, execute chaos drills, and inspect real-time cloud telemetry.

November 10 13:55 setup: [storefront](https://d1oj35ccg258u3.cloudfront.net) and [local dashboard](http://localhost:8501). The dashboard server was restarted; no browser checks, pytest, purchases, chaos or load drills were run for this rebuild, as requested. [Redeployment evidence](../docs/report/evidence/2026-11-10-restart/redeploy.json) records retained orders/stock and completed setup. The [earlier 00:37 results](../docs/report/evidence/2026-11-10-restart/results.json), including 112 offline passes/two tab renders, remain historical. Teardown is paused and services remain running; no automatic teardown is configured. The dashboard is local to this machine, separate from the AWS storefront.

---

## Quick Start

From the `fashionstore/` directory:

### Option 1: Via Makefile (using `uv` or installed Python)
```bash
make dashboard
```

### Option 2: Directly via `uv` (Zero-install)
```bash
uv run --with streamlit --with boto3 --with requests --with pytest --with pandas streamlit run dashboard/app.py
```

### Option 3: Standard Python / venv
```bash
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```

Once launched, open `http://localhost:8501` in your browser.

Before running live drills:

- Deploy the demo and sign in to AWS; the dashboard reads the demo Terraform outputs.
- Set `FS_USER_A_EMAIL` to a dedicated Cognito test shopper and `FS_TEST_PASSWORD` to its password. Use an SES-verified recipient while the demo is in the SES sandbox. The payment drill replaces this shopper's cart and creates a real order.
- Authenticated load tests also require distinct `loadtest+N@example.com` shoppers in this deployment using `FS_TEST_PASSWORD`. The selected profile determines how many are needed; missing or invalid tokens stop the run.
- The example.com load-test recipients are not SES-verified; notification delivery can fail in the sandbox even when checkout succeeds.

**Clear Display** clears the selected drill's saved output and restarts its telemetry display baseline. It does not change AWS resources, purge queues, reset inventory or recover a failed drill.

## Offline Dashboard Tests

From `fashionstore/`, run the same command used by the CI `functions` job:

```bash
python -m pip install -r functions/requirements-dev.txt
python -m pytest dashboard -q --confcutdir=dashboard -o "markers=chaos: live-stack drill exercised with mocks in this suite"
```

These tests mock AWS, HTTP and subprocess calls; they require no deployed stack or AWS credentials. The dashboard-only collection excludes the live-test fixtures in `tests/conftest.py`. The marker declaration registers the imported chaos test without hiding warnings.

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
   * **Payment Outage**: Validates the test shopper and cart, throttles `payment-api` Lambda to 0 concurrency, submits a checkout, and checks that it remains `PENDING` after 45 seconds. Restores the original concurrency and polls for up to 420 seconds for `CONFIRMED`, allowing for the queue's 180-second visibility timeout. Allow roughly eight minutes plus sign-in and API calls. Rejection or timeout fails the drill; success proves acceptance during the outage and confirmation after restoration, without proving a worker attempted payment during the outage.
   * **Synthetic DLQ Redrive**: Sends one valid synthetic message directly to an empty `checkout-dlq`, starts redrive and checks for worker confirmation. This tests redrive and processing, not retry exhaustion or an API-created checkout.
   * **Abrupt Pod Kill**: Requires at least two Ready v1 pods, deletes one, samples the catalogue API and checks replacement readiness. Successful samples show recovery during those observations; they do not prove uninterrupted availability.
   * **SQS Partition & Reconciler**: Simulates store-api pod network partition and demonstrates the background `@Scheduled` reconciler recovering missed orders.
   * **Flash Sale Concurrency**: Runs competing purchases of `FLASH-001`, records outcomes and checks that final stock is nonnegative. Cross-check the database separately to reconcile confirmed orders against initial stock. Reseed before each run; no live result is claimed for this handoff.
2. **Load & Concurrency Benchmarks (k6)**:
   * **Full System Performance**: Benchmarks browse and checkout paths across CloudFront, ALB, and EKS.
   * **CloudWatch Telemetry**: Visualizes ingress traffic, p95 latency, and RDS database load in real time.
3. **Cloud Safety Telemetry & Budget**:
   * Inspects SQS queue depths, in-flight messages, and CloudWatch alarms.
   * Displays reported spend against the US$100 student alert budget from AWS Budgets. Billing is delayed and alerts do not cap spending. The preflight November 1–9 snapshot showed about US$6.30 usage offset by credits; it is not a verified remaining-credit balance or final restart cost.
