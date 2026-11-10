# FashionStore final presentation: content structure

Prepared: 9 November 2026. Verification status updated: 10 November 2026.

Based on the locally supplied `FashionStore on AWS — IS458 Group 6 Final Presentation.pptx.pdf`.

The [current storefront](https://d1oj35ccg258u3.cloudfront.net) and [local dashboard](http://localhost:8501) were set up at 13:55 on November 10. [Redeployment evidence](report/evidence/2026-11-10-restart/redeploy.json) records 63 creates with existing orders/stock retained. The owner requested no tests: this rebuild was not functionally retested. The [00:37 results](report/evidence/2026-11-10-restart/results.json)—31 API passes/four skips, three browser passes/one skip, seven private-access passes and 112 offline dashboard passes—remain historical evidence for existing source-build tag [`v0.1.0`](https://github.com/sxtay1914/IS458/tree/v0.1.0). Teardown is paused after the owner's reversal; services remain running with no automatic shutdown.

The presentation follows this order:

**Use cases → Implementation architecture with integrated demos → Monitoring and alerts → Six pillars → Key learnings.**

Each architecture walkthrough answers three questions: which use case does this support, how does it work, and what can we demonstrate?

## 1. High-level structure

Suggested length: **14 main slides**, followed by backup slides.

| Section | Slides | Purpose |
| --- | --- | --- |
| Use cases | 1–2 | Establish the problem and expected user outcomes. |
| Implementation architecture + integrated demos | 3–9 | Show the overall system, then follow each use case through its components. |
| Monitoring and alerts | 10 | Explain how operators detect and investigate problems. |
| Six pillars | 11 | Evaluate the implementation's strengths and trade-offs. |
| Key learnings and limitations | 12–14 | Explain what failed, what changed, and what remains. |

There is no separate demo section. Show the relevant architecture path, explain its safeguards, then demonstrate its outcome.

## 2. Detailed slide structure

| Slide | Title | Content and integrated demonstration |
| --- | --- | --- |
| **1** | **FashionStore: the problem we are solving** | Introduce flash-sale traffic, limited stock and duplicate checkout attempts. State the Part B implementation scope and budget. Keep the business context brief. |
| **2** | **Our four use cases** | **UC1:** browse and manage a private cart. **UC2:** purchase without overselling or duplicate orders. **UC3:** check the outcome and view owned orders. **UC4:** receive an outcome email. Give each an observable acceptance criterion. |
| **3** | **Implementation architecture: the complete system** | Show the Part B overview with three highlighted paths: browsing/cart, checkout processing, and notifications. Identify public entry points and private backend resources. Briefly distinguish the implemented Part B from the proposed Part A. |
| **4** | **UC1: browsing and managing a private cart** | Explain CloudFront → S3 for the storefront, Cognito for sign-in, and CloudFront → VPC origin → internal ALB → EKS → RDS for cart requests. Explain ownership checks. **Demo:** browse, sign in, add an item and change its quantity. |
| **5** | **UC2: accepting checkout during a traffic spike** | Explain saving PENDING before dispatching to SQS, returning `202`, and processing asynchronously through Lambda. Explain why limiting worker concurrency protects database capacity. **Demo:** submit checkout and show the pending state and checkout ID. |
| **6** | **UC2: protecting stock and preventing duplicate orders** | Explain conditional stock updates, transactions, unique checkout IDs and idempotency keys. **Evidence/demo:** replay the same checkout key and show one order; present the MySQL race test with **50 confirmed, 70 rejected and stock 0** from 120 competing purchases. Label the race test as an automated test against real MySQL, separate from live AWS load testing. |
| **7** | **UC3: showing the correct outcome to the correct shopper** | Explain how the worker records CONFIRMED or REJECTED, how the browser polls the API, and how order ownership is enforced. **Demo:** follow the checkout to completion, open its order and show a prepared rejected-payment example. |
| **8** | **UC4: notifying the shopper** | Explain SNS → notifier Lambda → SES. Show how `notification_log` suppresses duplicate attempts. **Demo:** open the email corresponding to the checkout. State the remaining duplicate-email risk if sending succeeds but recording SENT fails. |
| **9** | **Supporting the use cases: scaling and controlled releases** | Explain HPA scaling for API traffic, the checkout concurrency cap, and ALB's 90/10 v1/v2 routing. Briefly show Terraform, CI and manual deployment. **Evidence:** HPA output and version-routing results; distinguish configured behaviour from behaviour actually tested. |
| **10** | **Monitoring and alerts: detecting and investigating failures** | Explain the signals monitored: queue backlog/age, DLQ messages, Lambda errors, ALB failures, unhealthy pods and database pressure. Trace the alert path: CloudWatch alarm → SNS → operator email. **Evidence:** alarm screenshot, email and the operator's next action—inspect logs, correct the cause and safely redrive messages. Identify whether an alarm demonstration used direct DLQ injection or repeated processing failures. |
| **11** | **Evaluating our implementation against the six pillars** | Map each pillar to a concrete implementation decision and its limitation. Use the table below rather than six generic definitions. |
| **12** | **Key learning: passing tests did not cover every race condition** | Explain the cart deadlock, why existing tests missed it, and the scoped `READ_COMMITTED` fix. Show failing regression → fix → **27 passing local API tests on 8 November** → **corrected live purchase in the 10 November 00:37 results**. The later 13:55 rebuild was not retested. |
| **13** | **Key learnings: operating a real cloud deployment** | Use three concrete lessons: queued processing still needs database safeguards; infrastructure provisioning is only part of deployment; budget alerts need to be paired with teardown and cleanup verification. Tie each lesson to an experience from the project. |
| **14** | **Limitations and next steps** | State what the evidence establishes and what remains: live dashboard chaos/load evidence, single-AZ availability limits, simulated payments, SES sandbox and origin HTTPS. Prioritise the next improvements, then move to Q&A. |

## 3. Content for the six-pillars slide

| Pillar | What we implemented | Trade-off or remaining gap |
| --- | --- | --- |
| **Operational excellence** | Terraform, CI, logs, runbooks and release controls. | Deployment and recovery still require manual steps. |
| **Security** | Cognito, ownership checks, private backend resources, workload IAM and database TLS. | CloudFront-to-ALB connection still uses HTTP. |
| **Reliability** | Transactions, idempotency, SQS retries, reconciler and DLQ. | Single-AZ workers/RDS; email delivery is not exactly once. |
| **Performance efficiency** | CloudFront caching, asynchronous checkout and API autoscaling. | Queueing adds completion delay; tested capacity must be stated accurately. |
| **Cost optimisation** | Small resources, budget alerts and teardown after testing. | EKS and NAT incur baseline charges while running. |
| **Sustainability** | Scale-in, arm64 Lambdas, storage lifecycle rules and teardown. | No measured energy or carbon reduction. |

## 4. Backup slides

- Full Part A production proposal and the differences from Part B.
- Full implementation diagram and resource configuration details.
- Detailed test results, load-test parameters and dated screenshots.
- Cost calculation and deployment/teardown evidence.
- Likely technical questions about idempotency, inventory, queue retries and recovery.

## 5. Evidence notes before finalising the slides

- Label 5,000 shoppers as a design target, not a demonstrated capacity. A 300-user run does not establish that capacity.
- Attach the original run evidence for the newer load figures. They were not independently verified during this presentation review.
- Label scaling accurately: v1 replicas 2 → 3 means total API pods 3 → 4 when the v2 replica is included.
- Use “50 confirmed orders” rather than “only 50 order rows”; rejected outcomes are also stored.
- Describe notification deduplication without promising exactly-once email delivery.
- Distinguish infrastructure provisioning time from the full application deployment and verification time.
- Replace cost placeholders with measured spending and identify the measurement period.
- The cart fix is commit `49cc9e8`. Its [local evidence](report/evidence/2026-11-08-cart-deadlock/results.json) covers MySQL testing on 8 November; [November 10 00:37 evidence](report/evidence/2026-11-10-restart/results.json) records three passing live browser journeys. Do not present these as tests of the later 13:55 rebuild.
- Label the November 1–9 preflight usage of about US$6.30 as delayed billing data offset by credits. It is not remaining credit balance or the final restart cost.
- A synthetic direct-to-DLQ drill verifies redrive/worker processing, not exhausted retries. Pod deletion with successful API samples does not prove uninterrupted availability; neither dashboard drill was run live at this handoff.

This document proposes slide content. It does not modify the presentation PDF or record a new deployment/test run.
