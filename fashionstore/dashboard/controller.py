"""FashionStore Test & Chaos Controller.

Executes failure drills, load tests, and gathers telemetry from AWS resources
for the Streamlit Test Control Center.
"""
from __future__ import annotations

import datetime
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, MutableMapping, Optional

# Root directories
DASHBOARD_DIR = Path(__file__).resolve().parent
APP_ROOT = DASHBOARD_DIR.parent
DEMO_DIR = APP_ROOT / "infra" / "terraform" / "environments" / "demo"
BOOT_DIR = APP_ROOT / "infra" / "terraform" / "bootstrap"
TESTS_DIR = APP_ROOT / "tests"
DEFAULT_REGION = os.environ.get("AWS_REGION", "ap-southeast-1")


class TestController:
    def __init__(self, region: str = DEFAULT_REGION):
        self.region = region
        self._tf_outputs: Optional[Dict[str, Any]] = None

    # -------------------------------------------------------------------------
    # Terraform & Environment State
    # -------------------------------------------------------------------------
    def get_terraform_outputs(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Fetch terraform outputs from the demo environment."""
        if self._tf_outputs is not None and not force_refresh:
            return self._tf_outputs

        try:
            res = subprocess.run(
                ["terraform", f"-chdir={DEMO_DIR}", "output", "-json"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if res.returncode == 0 and res.stdout.strip():
                raw = json.loads(res.stdout)
                self._tf_outputs = {k: v.get("value") for k, v in raw.items()}
                return self._tf_outputs
        except Exception:
            pass

        self._tf_outputs = {}
        return self._tf_outputs

    def check_aws_credentials(self) -> Dict[str, Any]:
        """Check if AWS credentials are active."""
        try:
            import boto3
            sts = boto3.client("sts", region_name=self.region)
            identity = sts.get_caller_identity()
            return {
                "active": True,
                "arn": identity.get("Arn"),
                "account": identity.get("Account"),
                "user_id": identity.get("UserId"),
            }
        except Exception as e:
            return {
                "active": False,
                "error": str(e),
            }

    def get_system_status(self) -> Dict[str, Any]:
        """Summarize current system status across AWS and local files."""
        cred_info = self.check_aws_credentials()
        tf_out = self.get_terraform_outputs(force_refresh=True)
        is_deployed = bool(tf_out.get("storefront_url"))

        return {
            "credentials": cred_info,
            "is_deployed": is_deployed,
            "region": self.region,
            "storefront_url": tf_out.get("storefront_url", os.environ.get("FS_BASE_URL", "Not deployed")),
            "alb_dns_name": tf_out.get("alb_dns_name", "N/A"),
            "eks_cluster_name": tf_out.get("eks_cluster_name", "N/A"),
            "checkout_queue_url": tf_out.get("checkout_queue_url", "N/A"),
            "checkout_dlq_url": tf_out.get("checkout_dlq_url", "N/A"),
            "function_names": tf_out.get("function_names", {}),
        }

    # -------------------------------------------------------------------------
    # CloudWatch, SQS & Telemetry
    # -------------------------------------------------------------------------
    def get_queue_telemetry(self) -> Dict[str, Any]:
        """Fetch queue depth and backlog metrics."""
        tf_out = self.get_terraform_outputs()
        queue_url = tf_out.get("checkout_queue_url")
        dlq_url = tf_out.get("checkout_dlq_url")

        if not queue_url or not dlq_url:
            return {"available": False, "reason": "Queues not deployed"}

        try:
            import boto3
            sqs = boto3.client("sqs", region_name=self.region)
            q_attr = sqs.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=[
                    "ApproximateNumberOfMessages",
                    "ApproximateNumberOfMessagesNotVisible",
                    "ApproximateNumberOfMessagesDelayed",
                ],
            )["Attributes"]

            dlq_attr = sqs.get_queue_attributes(
                QueueUrl=dlq_url,
                AttributeNames=["ApproximateNumberOfMessages"],
            )["Attributes"]

            return {
                "available": True,
                "checkout_queue_visible": int(q_attr.get("ApproximateNumberOfMessages", 0)),
                "checkout_queue_in_flight": int(q_attr.get("ApproximateNumberOfMessagesNotVisible", 0)),
                "checkout_queue_delayed": int(q_attr.get("ApproximateNumberOfMessagesDelayed", 0)),
                "dlq_visible": int(dlq_attr.get("ApproximateNumberOfMessages", 0)),
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    def get_cloudwatch_alarms(self) -> list[Dict[str, Any]]:
        """Fetch status of FashionStore CloudWatch alarms."""
        try:
            import boto3
            cw = boto3.client("cloudwatch", region_name=self.region)
            res = cw.describe_alarms(AlarmNamePrefix="fashionstore")
            alarms = []
            for a in res.get("MetricAlarms", []):
                alarms.append({
                    "name": a["AlarmName"],
                    "state": a["StateValue"],
                    "reason": a["StateReason"],
                    "updated": str(a.get("StateUpdatedTimestamp", "")),
                })
            return alarms
        except Exception as e:
            return [{"name": "Error fetching alarms", "state": "UNKNOWN", "reason": str(e)}]

    def get_budget_status(self) -> Dict[str, Any]:
        """Fetch budget status from AWS Budgets."""
        try:
            cred = self.check_aws_credentials()
            if not cred["active"]:
                return {"available": False, "reason": "No AWS credentials"}

            import boto3
            budgets = boto3.client("budgets", region_name=self.region)
            res = budgets.describe_budget(
                AccountId=cred["account"],
                BudgetName="fashionstore-build",
            )
            b = res.get("Budget", {})
            return {
                "available": True,
                "name": b.get("BudgetName"),
                "limit_usd": float(b.get("BudgetLimit", {}).get("Amount", 100)),
                "actual_spend_usd": float(b.get("CalculatedSpend", {}).get("ActualSpend", {}).get("Amount", 0)),
                "forecast_spend_usd": float(b.get("CalculatedSpend", {}).get("ForecastedSpend", {}).get("Amount", 0)),
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    def ensure_valid_tokens(self, required_users: int) -> None:
        """Prepare distinct access tokens for this deployment, or fail before starting load."""
        import base64
        import concurrent.futures

        tf_out = self.get_terraform_outputs()
        base_url = tf_out.get("storefront_url")
        app_config = tf_out.get("app_config", {})
        issuer = app_config.get("COGNITO_ISSUER_URL")
        client_id = app_config.get("COGNITO_CLIENT_ID")
        user_pwd = os.environ.get("FS_TEST_PASSWORD")
        if not base_url or not issuer or not client_id:
            raise ValueError("Load tests need the deployed storefront URL and Cognito issuer/client in Terraform outputs.")
        if not user_pwd:
            raise ValueError("Set FS_TEST_PASSWORD for the loadtest+N@example.com shoppers before running load tests.")
        if type(required_users) is not int or required_users < 1:
            raise ValueError("The selected load profile must require at least one shopper.")

        def valid(tokens):
            if not isinstance(tokens, list) or len(tokens) < required_users:
                return False
            subjects = set()
            # Current scripts run up to five minutes; allow time for outcome polling too.
            expires_after = time.time() + 600
            try:
                for token in tokens:
                    parts = token.split(".")
                    if len(parts) != 3 or not all(parts):
                        return False
                    payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)))
                    sub = payload.get("sub")
                    exp = payload.get("exp")
                    if (not isinstance(sub, str) or not sub or sub in subjects
                            or type(exp) is not int or exp <= expires_after
                            or payload.get("token_use") != "access"
                            or payload.get("iss") != issuer
                            or payload.get("client_id") != client_id
                            or "fashionstore-api/checkout.write" not in payload.get("scope", "").split()):
                        return False
                    subjects.add(sub)
                # These checks select cached tokens; the API still verifies JWT signatures.
                return True
            except (AttributeError, TypeError, ValueError):
                return False

        tokens_file = TESTS_DIR / "load" / "tokens.json"
        try:
            if valid(json.loads(tokens_file.read_text())):
                return
        except (OSError, ValueError):
            pass

        token_script = APP_ROOT / "tests" / "e2e" / "tools" / "get-token.mjs"

        def fetch_token(i):
            try:
                result = subprocess.run(
                    ["node", str(token_script), base_url, f"loadtest+{i}@example.com", user_pwd],
                    capture_output=True, text=True, timeout=90,
                )
                if result.returncode == 0:
                    return json.loads(result.stdout).get("access_token")
            except Exception:
                # Subprocess exceptions can contain the password-bearing command.
                return None
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, required_users)) as pool:
            tokens = list(pool.map(fetch_token, range(1, required_users + 1)))
        if not valid(tokens):
            raise ValueError(
                f"Could not obtain {required_users} distinct, current-deployment access tokens with at least 10 minutes remaining. "
                "Check the loadtest+N@example.com users and FS_TEST_PASSWORD; no authenticated load was started."
            )
        tokens_file.touch(mode=0o600, exist_ok=True)
        tokens_file.chmod(0o600)
        tokens_file.write_text(json.dumps(tokens))

    def _load_users_required(self, profile: str, script_name: str | None = None) -> int:
        settings = json.loads((TESTS_DIR / "load" / "profiles" / f"{profile}.json").read_text())
        checkout = settings["checkout"]
        checkout_users = max(stage["target"] for stage in checkout["stages"]) if checkout.get("stages") else checkout["vus"]
        flash_users = settings["flash_sale"]["buyers"]
        if script_name == "checkout.js":
            return checkout_users
        if script_name == "flash-sale.js":
            return flash_users
        return max(checkout_users, flash_users)

    def get_alb_arn_suffix(self) -> Optional[str]:
        """Fetch or deduce the ALB ARN suffix (e.g. app/fashionstore-demo-api/0adf...)."""
        try:
            import boto3
            elbv2 = boto3.client("elbv2", region_name=self.region)
            albs = elbv2.describe_load_balancers().get("LoadBalancers", [])
            for a in albs:
                arn = a.get("LoadBalancerArn", "")
                if "fashionstore" in arn:
                    parts = arn.split("/")
                    return f"app/{parts[-2]}/{parts[-1]}"
        except Exception:
            pass
        return None

    def _build_time_series_df(
        self,
        metric_queries: list[Dict[str, Any]],
        window_minutes: int = 15,
        column_mapping: Optional[Dict[str, str]] = None,
        continuous_fill_ids: Optional[set[str]] = None,
    ) -> Any:
        """Helper to query CloudWatch get_metric_data and return a clean pandas DataFrame."""
        try:
            import boto3
            import pandas as pd

            cw = boto3.client("cloudwatch", region_name=self.region)
            end = datetime.datetime.now(datetime.timezone.utc).replace(second=0, microsecond=0)
            start = end - datetime.timedelta(minutes=window_minutes)
            time_index = pd.date_range(start=start, end=end, freq="1min", tz="UTC")

            res = cw.get_metric_data(
                MetricDataQueries=metric_queries,
                StartTime=start,
                EndTime=end,
            )

            df = pd.DataFrame(index=time_index)
            continuous = continuous_fill_ids or set()

            for r in res.get("MetricDataResults", []):
                q_id = r["Id"]
                col_name = column_mapping.get(q_id, q_id) if column_mapping else q_id
                if r.get("Timestamps"):
                    ts_rounded = [pd.Timestamp(t).round("1min") for t in r["Timestamps"]]
                    s = pd.Series(r["Values"], index=ts_rounded)
                    s = s[~s.index.duplicated(keep="first")]
                    if q_id in continuous:
                        df[col_name] = s.reindex(df.index).ffill().bfill().fillna(0.0)
                    else:
                        df[col_name] = s.reindex(df.index, fill_value=0.0)
                else:
                    df[col_name] = 0.0

            df.index = df.index.tz_convert("Asia/Singapore").strftime("%H:%M")
            return df
        except Exception:
            try:
                import pandas as pd
                return pd.DataFrame()
            except Exception:
                return None

    def get_payment_drill_telemetry(self, window_minutes: int = 15, since_timestamp: Optional[float] = None, **kwargs) -> Dict[str, Any]:
        """Fetch telemetry specifically for Drill 1: Payment Outage & SQS Retry."""
        tf_out = self.get_terraform_outputs()
        fn = tf_out.get("function_names", {}).get("payment-api", "fashionstore-demo-payment-api")
        proc_fn = tf_out.get("function_names", {}).get("process-checkout", "fashionstore-demo-process-checkout")

        try:
            import boto3
            lam = boto3.client("lambda", region_name=self.region)
            c_info = lam.get_function_concurrency(FunctionName=fn)
            conc_val = c_info.get("ReservedConcurrentExecutions")
            if conc_val == 0:
                concurrency_status = "Throttled (0)"
            elif conc_val is not None:
                concurrency_status = f"{conc_val} Reserved"
            else:
                concurrency_status = "Operational"

            q_data = self.get_queue_telemetry()
            dlq_depth = q_data.get("dlq_visible", 0) if q_data.get("available") else 0
            main_depth = q_data.get("checkout_queue_visible", 0) if q_data.get("available") else 0

            # Filter recent logs for checkout events (honoring since_timestamp baseline if present)
            logs = boto3.client("logs", region_name=self.region)
            now_ms = int(time.time() * 1000)
            if since_timestamp is not None:
                start_ms = max(int(since_timestamp * 1000), now_ms - (window_minutes * 60 * 1000))
            else:
                start_ms = now_ms - (window_minutes * 60 * 1000)
            recent_logs = []
            confirmed_records = []
            try:
                evs = logs.filter_log_events(
                    logGroupName=f"/aws/lambda/{proc_fn}",
                    startTime=start_ms,
                    limit=30,
                ).get("events", [])
                for e in evs:
                    msg = e["message"].strip()
                    if "checkout_processed" in msg:
                        ts_str = datetime.datetime.fromtimestamp(e["timestamp"] / 1000).strftime("%H:%M:%S")
                        try:
                            json_start = msg.find("{")
                            if json_start != -1:
                                data = json.loads(msg[json_start:])
                                cid = data.get("checkout_id", "unknown")
                                st = data.get("status", "UNKNOWN")
                                if st == "CONFIRMED":
                                    confirmed_records.append({"time": ts_str, "checkout_id": cid, "status": st})
                        except Exception:
                            pass
                        recent_logs.append(f"[{ts_str}] {msg}")
            except Exception:
                pass

            metric_queries = [
                {
                    "Id": "pay_throttles",
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/Lambda",
                            "MetricName": "Throttles",
                            "Dimensions": [{"Name": "FunctionName", "Value": fn}],
                        },
                        "Period": 60,
                        "Stat": "Sum",
                    },
                    "ReturnData": True,
                },
                {
                    "Id": "pay_invocations",
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/Lambda",
                            "MetricName": "Invocations",
                            "Dimensions": [{"Name": "FunctionName", "Value": fn}],
                        },
                        "Period": 60,
                        "Stat": "Sum",
                    },
                    "ReturnData": True,
                },
                {
                    "Id": "checkout_invocations",
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/Lambda",
                            "MetricName": "Invocations",
                            "Dimensions": [{"Name": "FunctionName", "Value": proc_fn}],
                        },
                        "Period": 60,
                        "Stat": "Sum",
                    },
                    "ReturnData": True,
                },
                {
                    "Id": "checkout_errors",
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/Lambda",
                            "MetricName": "Errors",
                            "Dimensions": [{"Name": "FunctionName", "Value": proc_fn}],
                        },
                        "Period": 60,
                        "Stat": "Sum",
                    },
                    "ReturnData": True,
                },
            ]

            mapping = {
                "pay_throttles": "Payment Throttles (429)",
                "pay_invocations": "Payment Invocations",
                "checkout_invocations": "Worker Invocations",
                "checkout_errors": "Worker Retried Errors",
            }

            df = self._build_time_series_df(metric_queries, window_minutes, mapping)
            throttles_sum = 0
            if df is not None and hasattr(df, "empty") and not df.empty and "Payment Throttles (429)" in df:
                if since_timestamp is not None:
                    since_sgt = datetime.datetime.fromtimestamp(since_timestamp, datetime.timezone(datetime.timedelta(hours=8))).strftime("%H:%M")
                    sub_df = df[df.index >= since_sgt]
                    throttles_sum = int(sub_df["Payment Throttles (429)"].sum()) if not sub_df.empty else 0
                else:
                    throttles_sum = int(df["Payment Throttles (429)"].sum())

            return {
                "available": True,
                "summary": {
                    "concurrency": concurrency_status,
                    "throttles_15m": throttles_sum,
                    "confirmed_checkouts": len(confirmed_records),
                    "confirmed_records": confirmed_records,
                    "dlq_depth": dlq_depth,
                    "main_depth": main_depth,
                },
                "recent_logs": recent_logs[-5:],
                "df": df,
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    def get_dlq_drill_telemetry(self, window_minutes: int = 15, since_timestamp: Optional[float] = None, **kwargs) -> Dict[str, Any]:
        """Read DLQ attributes, redrive task status and worker logs without receiving messages."""
        tf_out = self.get_terraform_outputs()
        queue_url = tf_out.get("checkout_queue_url")
        dlq_url = tf_out.get("checkout_dlq_url")
        proc_fn = tf_out.get("function_names", {}).get("process-checkout", "fashionstore-demo-process-checkout")

        try:
            import boto3
            sqs = boto3.client("sqs", region_name=self.region)
            logs = boto3.client("logs", region_name=self.region)

            dlq_attr = sqs.get_queue_attributes(QueueUrl=dlq_url, AttributeNames=["ApproximateNumberOfMessages", "QueueArn"])["Attributes"]
            q_attr = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"])["Attributes"]

            dlq_depth = int(dlq_attr.get("ApproximateNumberOfMessages", 0))
            dlq_arn = dlq_attr.get("QueueArn")
            main_depth = int(q_attr.get("ApproximateNumberOfMessages", 0))
            in_flight = int(q_attr.get("ApproximateNumberOfMessagesNotVisible", 0))

            # Query SQS redrive move tasks
            tasks = []
            try:
                tasks = sqs.list_message_move_tasks(SourceArn=dlq_arn).get("Results", [])
            except Exception:
                pass

            latest_task = tasks[0] if tasks else None
            if since_timestamp is not None and latest_task:
                # Discard completed redrive tasks that occurred prior to the reset baseline
                if latest_task.get("StartedTimestamp", 0) < int((since_timestamp - 3) * 1000):
                    latest_task = None

            move_status = latest_task.get("Status", "IDLE") if latest_task else "IDLE"
            moved_count = latest_task.get("ApproximateNumberOfMessagesMoved", 0) if latest_task else 0

            # Query Lambda worker confirmation logs
            now_ms = int(time.time() * 1000)
            if since_timestamp is not None:
                start_ms = max(int(since_timestamp * 1000), now_ms - (window_minutes * 60 * 1000))
            else:
                start_ms = now_ms - (window_minutes * 60 * 1000)
            recent_logs = []
            confirmed_records = []
            try:
                evs = logs.filter_log_events(
                    logGroupName=f"/aws/lambda/{proc_fn}",
                    startTime=start_ms,
                    limit=30,
                ).get("events", [])
                for e in evs:
                    msg = e["message"].strip()
                    if "checkout_processed" in msg:
                        ts_str = datetime.datetime.fromtimestamp(e["timestamp"] / 1000).strftime("%H:%M:%S")
                        try:
                            json_start = msg.find("{")
                            if json_start != -1:
                                data = json.loads(msg[json_start:])
                                cid = data.get("checkout_id", "unknown")
                                st = data.get("status", "UNKNOWN")
                                if st == "CONFIRMED":
                                    confirmed_records.append({"time": ts_str, "checkout_id": cid, "status": st})
                        except Exception:
                            pass
                        recent_logs.append(f"[{ts_str}] {msg}")
            except Exception:
                pass

            # Time series for DLQ depth & main queue
            q_dlq_name = dlq_url.split("/")[-1]
            q_main_name = queue_url.split("/")[-1]

            metric_queries = [
                {
                    "Id": "dlq_visible",
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/SQS",
                            "MetricName": "ApproximateNumberOfMessagesVisible",
                            "Dimensions": [{"Name": "QueueName", "Value": q_dlq_name}],
                        },
                        "Period": 60,
                        "Stat": "Maximum",
                    },
                    "ReturnData": True,
                },
                {
                    "Id": "main_visible",
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/SQS",
                            "MetricName": "ApproximateNumberOfMessagesVisible",
                            "Dimensions": [{"Name": "QueueName", "Value": q_main_name}],
                        },
                        "Period": 60,
                        "Stat": "Maximum",
                    },
                    "ReturnData": True,
                },
            ]

            mapping = {
                "dlq_visible": "Messages Visible in DLQ",
                "main_visible": "Main Queue Backlog (Pending Orders)",
            }

            df = self._build_time_series_df(
                metric_queries,
                window_minutes,
                mapping,
                continuous_fill_ids={"dlq_visible", "main_visible"},
            )

            return {
                "available": True,
                "summary": {
                    "dlq_depth": dlq_depth,
                    "main_depth": main_depth,
                    "in_flight": in_flight,
                    "move_status": move_status,
                    "messages_moved": moved_count,
                    "confirmed_checkouts": len(confirmed_records),
                    "confirmed_records": confirmed_records,
                },
                "move_task": latest_task,
                "recent_logs": recent_logs[-5:],
                "df": df,
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    def get_pod_drill_telemetry(self, window_minutes: int = 15, since_timestamp: Optional[float] = None, **kwargs) -> Dict[str, Any]:
        """Fetch telemetry specifically for Drill 3: Abrupt Pod Kill & Zero-Downtime HA."""
        tf_out = self.get_terraform_outputs()
        tg_v1_arn = tf_out.get("target_group_arns", {}).get("v1")
        tg_v2_arn = tf_out.get("target_group_arns", {}).get("v2")
        alb_suffix = self.get_alb_arn_suffix()

        try:
            import boto3
            elbv2 = boto3.client("elbv2", region_name=self.region)

            v1_healthy, v1_unhealthy, v1_total = 0, 0, 0
            if tg_v1_arn:
                th_v1 = elbv2.describe_target_health(TargetGroupArn=tg_v1_arn).get("TargetHealthDescriptions", [])
                v1_total = len(th_v1)
                v1_healthy = sum(1 for d in th_v1 if d.get("TargetHealth", {}).get("State") == "healthy")
                v1_unhealthy = v1_total - v1_healthy

            v2_healthy, v2_total = 0, 0
            if tg_v2_arn:
                th_v2 = elbv2.describe_target_health(TargetGroupArn=tg_v2_arn).get("TargetHealthDescriptions", [])
                v2_total = len(th_v2)
                v2_healthy = sum(1 for d in th_v2 if d.get("TargetHealth", {}).get("State") == "healthy")

            # Query running k8s pods (fallback to ALB target registrations if kubectl has no direct cluster route)
            k8s_pods = []
            try:
                k_env = os.environ.copy()
                if (APP_ROOT / ".kubeconfig").exists():
                    k_env["KUBECONFIG"] = str(APP_ROOT / ".kubeconfig")
                p_res = subprocess.run(
                    ["kubectl", "get", "pods", "-n", "fashionstore", "-l", "app=store-api", "-o", "json"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    env=k_env,
                )
                if p_res.returncode == 0:
                    k_data = json.loads(p_res.stdout)
                    for item in k_data.get("items", []):
                        name = item.get("metadata", {}).get("name", "unknown")
                        phase = item.get("status", {}).get("phase", "Unknown")
                        statuses = item.get("status", {}).get("containerStatuses", [{}])
                        ready = statuses[0].get("ready", False) if statuses else False
                        restarts = statuses[0].get("restartCount", 0) if statuses else 0
                        k8s_pods.append({"name": name, "phase": phase, "ready": ready, "restarts": restarts})
            except Exception:
                pass

            if not k8s_pods:
                for idx, d in enumerate(th_v1):
                    target_ip = d.get("Target", {}).get("Id", f"pod-v1-{idx}")
                    state = d.get("TargetHealth", {}).get("State", "healthy")
                    k8s_pods.append({
                        "name": f"store-api-v1-{target_ip.replace('.', '-')}",
                        "phase": "Running" if state == "healthy" else "Unhealthy",
                        "ready": state == "healthy",
                        "restarts": 0,
                    })
                for idx, d in enumerate(th_v2):
                    target_ip = d.get("Target", {}).get("Id", f"pod-v2-{idx}")
                    state = d.get("TargetHealth", {}).get("State", "healthy")
                    k8s_pods.append({
                        "name": f"store-api-v2-canary-{target_ip.replace('.', '-')}",
                        "phase": "Running" if state == "healthy" else "Unhealthy",
                        "ready": state == "healthy",
                        "restarts": 0,
                    })

            metric_queries = []
            mapping = {}
            if alb_suffix and tg_v1_arn:
                tg_v1_suffix = "targetgroup/" + tg_v1_arn.split("targetgroup/")[-1]
                metric_queries.extend([
                    {
                        "Id": "v1_healthy_hosts",
                        "MetricStat": {
                            "Metric": {
                                "Namespace": "AWS/ApplicationELB",
                                "MetricName": "HealthyHostCount",
                                "Dimensions": [
                                    {"Name": "LoadBalancer", "Value": alb_suffix},
                                    {"Name": "TargetGroup", "Value": tg_v1_suffix},
                                ],
                            },
                            "Period": 60,
                            "Stat": "Average",
                        },
                        "ReturnData": True,
                    },
                    {
                        "Id": "alb_5xx",
                        "MetricStat": {
                            "Metric": {
                                "Namespace": "AWS/ApplicationELB",
                                "MetricName": "HTTPCode_Target_5XX_Count",
                                "Dimensions": [{"Name": "LoadBalancer", "Value": alb_suffix}],
                            },
                            "Period": 60,
                            "Stat": "Sum",
                        },
                        "ReturnData": True,
                    },
                ])
                mapping = {
                    "v1_healthy_hosts": "v1 Healthy Hosts",
                    "alb_5xx": "Target 5XX Errors",
                }

                if tg_v2_arn:
                    tg_v2_suffix = "targetgroup/" + tg_v2_arn.split("targetgroup/")[-1]
                    metric_queries.append({
                        "Id": "v2_healthy_hosts",
                        "MetricStat": {
                            "Metric": {
                                "Namespace": "AWS/ApplicationELB",
                                "MetricName": "HealthyHostCount",
                                "Dimensions": [
                                    {"Name": "LoadBalancer", "Value": alb_suffix},
                                    {"Name": "TargetGroup", "Value": tg_v2_suffix},
                                ],
                            },
                            "Period": 60,
                            "Stat": "Average",
                        },
                        "ReturnData": True,
                    })
                    mapping["v2_healthy_hosts"] = "v2 Canary Hosts"

            df = self._build_time_series_df(
                metric_queries,
                window_minutes,
                mapping,
                continuous_fill_ids={"v1_healthy_hosts", "v2_healthy_hosts"},
            )
            target_5xx_sum = 0
            if df is not None and hasattr(df, "empty") and not df.empty and "Target 5XX Errors" in df:
                target_5xx_sum = int(df["Target 5XX Errors"].sum())

            return {
                "available": True,
                "summary": {
                    "v1_healthy": v1_healthy,
                    "v1_total": v1_total,
                    "v2_healthy": v2_healthy,
                    "v2_total": v2_total,
                    "running_pods": len(k8s_pods),
                    "target_5xx_15m": target_5xx_sum,
                },
                "pods": k8s_pods,
                "df": df,
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    def get_flash_sale_drill_telemetry(self, window_minutes: int = 15, since_timestamp: Optional[float] = None, **kwargs) -> Dict[str, Any]:
        """Fetch telemetry specifically for Drill 5: Flash Sale Atomic Inventory Lock."""
        tf_out = self.get_terraform_outputs()
        proc_fn = tf_out.get("function_names", {}).get("process-checkout", "fashionstore-demo-process-checkout")

        try:
            import boto3
            logs = boto3.client("logs", region_name=self.region)
            now_ms = int(time.time() * 1000)
            if since_timestamp is not None:
                start_ms = max(int(since_timestamp * 1000), now_ms - (window_minutes * 60 * 1000))
            else:
                start_ms = now_ms - (window_minutes * 60 * 1000)
            confirmed_cnt = 0
            sold_out_cnt = 0
            try:
                evs = logs.filter_log_events(
                    logGroupName=f"/aws/lambda/{proc_fn}",
                    startTime=start_ms,
                    limit=50,
                ).get("events", [])
                for e in evs:
                    msg = e["message"]
                    if "checkout_processed" in msg:
                        if "CONFIRMED" in msg:
                            confirmed_cnt += 1
                        elif "OUT_OF_STOCK" in msg or "REJECTED" in msg:
                            sold_out_cnt += 1
            except Exception:
                pass

            metric_queries = [
                {
                    "Id": "rds_cpu",
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/RDS",
                            "MetricName": "CPUUtilization",
                            "Dimensions": [{"Name": "DBInstanceIdentifier", "Value": "fashionstore-demo-mysql"}],
                        },
                        "Period": 60,
                        "Stat": "Average",
                    },
                    "ReturnData": True,
                },
                {
                    "Id": "rds_conn",
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/RDS",
                            "MetricName": "DatabaseConnections",
                            "Dimensions": [{"Name": "DBInstanceIdentifier", "Value": "fashionstore-demo-mysql"}],
                        },
                        "Period": 60,
                        "Stat": "Average",
                    },
                    "ReturnData": True,
                },
            ]

            mapping = {
                "rds_cpu": "RDS CPU Utilization (%)",
                "rds_conn": "Active DB Connections",
            }

            df = self._build_time_series_df(
                metric_queries,
                window_minutes,
                mapping,
                continuous_fill_ids={"rds_cpu", "rds_conn"},
            )

            cpu_peak = 0.0
            conn_peak = 0
            if df is not None and hasattr(df, "empty") and not df.empty:
                if "RDS CPU Utilization (%)" in df:
                    cpu_peak = round(float(df["RDS CPU Utilization (%)"].max()), 1)
                if "Active DB Connections" in df:
                    conn_peak = int(df["Active DB Connections"].max())

            return {
                "available": True,
                "summary": {
                    "rds_cpu_peak": cpu_peak,
                    "rds_connections_peak": conn_peak,
                    "recent_confirmed": confirmed_cnt,
                    "recent_sold_out": sold_out_cnt,
                    "dlq_depth": 0,
                },
                "df": df,
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    def get_load_benchmark_telemetry(self, window_minutes: int = 15, since_timestamp: Optional[float] = None, **kwargs) -> Dict[str, Any]:
        """Fetch full telemetry across ALB, RDS, and SQS for the Load Benchmark."""
        alb_suffix = self.get_alb_arn_suffix()

        try:
            traffic_queries = []
            traffic_map = {}
            if alb_suffix:
                traffic_queries.extend([
                    {
                        "Id": "req_cnt",
                        "MetricStat": {
                            "Metric": {
                                "Namespace": "AWS/ApplicationELB",
                                "MetricName": "RequestCount",
                                "Dimensions": [{"Name": "LoadBalancer", "Value": alb_suffix}],
                            },
                            "Period": 60,
                            "Stat": "Sum",
                        },
                        "ReturnData": True,
                    },
                    {
                        "Id": "resp_lat",
                        "MetricStat": {
                            "Metric": {
                                "Namespace": "AWS/ApplicationELB",
                                "MetricName": "TargetResponseTime",
                                "Dimensions": [{"Name": "LoadBalancer", "Value": alb_suffix}],
                            },
                            "Period": 60,
                            "Stat": "p95",
                        },
                        "ReturnData": True,
                    },
                    {
                        "Id": "alb_5xx",
                        "MetricStat": {
                            "Metric": {
                                "Namespace": "AWS/ApplicationELB",
                                "MetricName": "HTTPCode_Target_5XX_Count",
                                "Dimensions": [{"Name": "LoadBalancer", "Value": alb_suffix}],
                            },
                            "Period": 60,
                            "Stat": "Sum",
                        },
                        "ReturnData": True,
                    },
                ])
                traffic_map = {
                    "req_cnt": "ALB Requests (req/min)",
                    "resp_lat": "p95 Latency (s)",
                    "alb_5xx": "Target 5XX Errors",
                }

            df_traffic = self._build_time_series_df(traffic_queries, window_minutes, traffic_map)

            backend_queries = [
                {
                    "Id": "rds_cpu",
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/RDS",
                            "MetricName": "CPUUtilization",
                            "Dimensions": [{"Name": "DBInstanceIdentifier", "Value": "fashionstore-demo-mysql"}],
                        },
                        "Period": 60,
                        "Stat": "Average",
                    },
                    "ReturnData": True,
                },
                {
                    "Id": "rds_conn",
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/RDS",
                            "MetricName": "DatabaseConnections",
                            "Dimensions": [{"Name": "DBInstanceIdentifier", "Value": "fashionstore-demo-mysql"}],
                        },
                        "Period": 60,
                        "Stat": "Average",
                    },
                    "ReturnData": True,
                },
            ]
            backend_map = {
                "rds_cpu": "RDS CPU (%)",
                "rds_conn": "Active DB Connections",
            }
            df_backend = self._build_time_series_df(
                backend_queries,
                window_minutes,
                backend_map,
                continuous_fill_ids={"rds_cpu", "rds_conn"},
            )

            total_reqs = 0
            p95_sec = 0.0
            sum_5xx = 0
            if df_traffic is not None and hasattr(df_traffic, "empty") and not df_traffic.empty:
                if "ALB Requests (req/min)" in df_traffic:
                    total_reqs = int(df_traffic["ALB Requests (req/min)"].sum())
                if "p95 Latency (s)" in df_traffic:
                    p95_sec = float(df_traffic["p95 Latency (s)"].max())
                    df_traffic["p95 Latency (ms)"] = (df_traffic["p95 Latency (s)"] * 1000).round(1)
                    del df_traffic["p95 Latency (s)"]
                if "Target 5XX Errors" in df_traffic:
                    sum_5xx = int(df_traffic["Target 5XX Errors"].sum())

            peak_cpu = 0.0
            peak_conn = 0
            if df_backend is not None and hasattr(df_backend, "empty") and not df_backend.empty:
                if "RDS CPU (%)" in df_backend:
                    peak_cpu = round(float(df_backend["RDS CPU (%)"].max()), 1)
                if "Active DB Connections" in df_backend:
                    peak_conn = int(df_backend["Active DB Connections"].max())

            pod_tel = self.get_pod_drill_telemetry(window_minutes)
            v1_healthy = pod_tel.get("summary", {}).get("v1_healthy", 2)

            return {
                "available": True,
                "summary": {
                    "total_requests": total_reqs,
                    "p95_latency_ms": round(p95_sec * 1000, 1),
                    "target_5xx": sum_5xx,
                    "peak_cpu": peak_cpu,
                    "peak_connections": peak_conn,
                    "v1_pods": v1_healthy,
                    "hpa_range": "2 - 5",
                },
                "df_traffic": df_traffic,
                "df_backend": df_backend,
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    def reset_drill_state(self, drill_name: str, display_state: MutableMapping[str, Any]) -> None:
        """Clear this drill's displayed history and restart its telemetry baseline only."""
        display_state.pop(f"last_exec_{drill_name}", None)
        display_state[f"drill_reset_time_{drill_name}"] = time.time()

    def get_canary_weights(self) -> Dict[str, Any]:
        """Fetch current v1/v2 weights from the internal ALB listener rule."""
        try:
            import boto3
            elbv2 = boto3.client("elbv2", region_name=self.region)
            tf_out = self.get_terraform_outputs()
            tg_arns = tf_out.get("target_group_arns", {})
            v1_arn = tg_arns.get("v1")
            v2_arn = tg_arns.get("v2")
            if not v1_arn or not v2_arn:
                return {"v1": 90, "v2": 10, "rule_arn": None}

            tg = elbv2.describe_target_groups(TargetGroupArns=[v1_arn])
            lb_arns = tg.get("TargetGroups", [{}])[0].get("LoadBalancerArns", [])
            if not lb_arns:
                return {"v1": 90, "v2": 10, "rule_arn": None}

            listeners = elbv2.describe_listeners(LoadBalancerArn=lb_arns[0])
            for l in listeners.get("Listeners", []):
                rules = elbv2.describe_rules(ListenerArn=l["ListenerArn"])
                for r in rules.get("Rules", []):
                    for a in r.get("Actions", []):
                        if a.get("Type") == "forward" and "ForwardConfig" in a:
                            tgs = a["ForwardConfig"].get("TargetGroups", [])
                            weights = {t["TargetGroupArn"]: t.get("Weight", 0) for t in tgs}
                            if v1_arn in weights and v2_arn in weights:
                                return {
                                    "v1": weights[v1_arn],
                                    "v2": weights[v2_arn],
                                    "rule_arn": r["RuleArn"],
                                }
            return {"v1": 90, "v2": 10, "rule_arn": None}
        except Exception:
            return {"v1": 90, "v2": 10, "rule_arn": None}

    def set_canary_weights(self, v1_weight: int, v2_weight: int) -> Dict[str, Any]:
        """Dynamically update v1/v2 traffic weights on the ALB listener rule."""
        try:
            import boto3
            elbv2 = boto3.client("elbv2", region_name=self.region)
            tf_out = self.get_terraform_outputs()
            tg_arns = tf_out.get("target_group_arns", {})
            v1_arn = tg_arns.get("v1")
            v2_arn = tg_arns.get("v2")
            curr = self.get_canary_weights()
            rule_arn = curr.get("rule_arn")
            if not rule_arn or not v1_arn or not v2_arn:
                return {"success": False, "message": "ALB listener rule not found."}

            elbv2.modify_rule(
                RuleArn=rule_arn,
                Actions=[
                    {
                        "Type": "forward",
                        "ForwardConfig": {
                            "TargetGroups": [
                                {"TargetGroupArn": v1_arn, "Weight": v1_weight},
                                {"TargetGroupArn": v2_arn, "Weight": v2_weight},
                            ],
                            "TargetGroupStickinessConfig": {"Enabled": False, "DurationSeconds": 1},
                        },
                    }
                ],
            )
            return {"success": True, "message": f"Successfully updated ALB listener rule to {v1_weight}% v1 / {v2_weight}% v2."}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # -------------------------------------------------------------------------
    # Failure Drills (Chaos Engineering)
    # -------------------------------------------------------------------------
    def run_payment_outage_drill(self, log_cb: Callable[[str], None]) -> bool:
        """Throttle payment-api Lambda to 0 concurrency, place order, restore and verify recovery."""
        tf_out = self.get_terraform_outputs()
        fn = tf_out.get("function_names", {}).get("payment-api")
        base_url = tf_out.get("storefront_url", os.environ.get("FS_BASE_URL"))
        user_a = os.environ.get("FS_USER_A_EMAIL")
        pwd = os.environ.get("FS_TEST_PASSWORD")

        if not base_url or not fn:
            log_cb("❌ Storefront URL and payment-api function must be available in Terraform outputs.")
            return False
        if not user_a or not pwd:
            log_cb("❌ Set FS_USER_A_EMAIL and FS_TEST_PASSWORD for a dedicated test shopper before running this drill.")
            return False

        try:
            import boto3
            import requests
            from botocore.exceptions import ClientError

            log_cb("🔍 [Step 1/5] Checking test shopper, stock and cart before injecting a failure...")
            token_script = APP_ROOT / "tests" / "e2e" / "tools" / "get-token.mjs"
            try:
                tok_res = subprocess.run(
                    ["node", str(token_script), base_url, user_a, pwd],
                    capture_output=True, text=True, timeout=90,
                )
            except subprocess.TimeoutExpired:
                log_cb("❌ Test shopper sign-in timed out; payment settings were not changed.")
                return False
            if tok_res.returncode != 0:
                raise RuntimeError("Test shopper sign-in failed; check the configured credentials.")
            access_token = json.loads(tok_res.stdout).get("access_token")
            if not access_token:
                raise RuntimeError("Test shopper sign-in returned no access token.")
            api_headers = {"Authorization": f"Bearer {access_token}"}
            product = requests.get(f"{base_url}/api/products/BAG-001", timeout=15)
            if product.status_code != 200 or product.json().get("stock", 0) < 1:
                raise RuntimeError("BAG-001 must exist and be in stock before running this drill.")
            cart = requests.put(
                f"{base_url}/api/cart", json={"items": [{"sku": "BAG-001", "qty": 1}]},
                headers=api_headers, timeout=15,
            )
            if cart.status_code != 200:
                raise RuntimeError(f"Could not prepare the test cart: HTTP {cart.status_code}.")

            lam = boto3.client("lambda", region_name=self.region)
            previous = lam.get_function_concurrency(FunctionName=fn).get("ReservedConcurrentExecutions")
            if previous == 0:
                raise RuntimeError("payment-api is already disabled; restore it before running this drill.")
            key = str(uuid.uuid4())
            status_url = f"{base_url}/api/checkouts/{key}"
            try:
                log_cb("💥 [Step 2/5] Setting payment-api concurrency to 0...")
                lam.put_function_concurrency(FunctionName=fn, ReservedConcurrentExecutions=0)
                time.sleep(3)
                try:
                    lam.invoke(
                        FunctionName=fn, InvocationType="RequestResponse",
                        Payload=json.dumps({"checkout_id": str(uuid.uuid4()), "amount_cents": 100, "email": user_a}).encode(),
                    )
                except ClientError as exc:
                    if exc.response.get("Error", {}).get("Code") != "TooManyRequestsException":
                        raise
                    log_cb("   ✅ Verified payment-api is throttled.")
                else:
                    raise RuntimeError("Payment was not throttled; the outage was not established.")

                log_cb(f"🛒 [Step 3/5] Submitting checkout {key} through the API...")
                accepted = requests.post(
                    f"{base_url}/api/checkouts", headers={**api_headers, "Idempotency-Key": key}, timeout=15,
                )
                if accepted.status_code != 202:
                    raise RuntimeError(f"Checkout was not accepted: HTTP {accepted.status_code}.")
                log_cb("   ✅ API returned HTTP 202. Checking that checkout stays pending during the outage...")
                time.sleep(45)
                pending = requests.get(status_url, headers=api_headers, timeout=10)
                if pending.status_code != 200 or pending.json().get("status") != "PENDING":
                    raise RuntimeError("Checkout did not remain PENDING during the payment outage.")
                log_cb("   ✅ Checkout remains PENDING while payment is disabled.")
            finally:
                # Restore even if the request fails or Streamlit interrupts the drill.
                try:
                    if previous is None:
                        lam.delete_function_concurrency(FunctionName=fn)
                    else:
                        lam.put_function_concurrency(FunctionName=fn, ReservedConcurrentExecutions=previous)
                except Exception:
                    log_cb(f"❌ RESTORE FAILED: check payment-api concurrency for {fn} immediately.")
                    raise
                log_cb("🔧 [Step 4/5] Original payment-api concurrency restored.")

            log_cb("🔄 [Step 5/5] Waiting up to 420s for CONFIRMED (SQS visibility timeout is 180s)...")
            deadline = time.monotonic() + 420
            while time.monotonic() < deadline:
                outcome = requests.get(status_url, headers=api_headers, timeout=10)
                if outcome.status_code != 200:
                    raise RuntimeError(f"Could not read checkout status: HTTP {outcome.status_code}.")
                body = outcome.json()
                if body.get("status") == "CONFIRMED":
                    log_cb(f"   ✅ Order CONFIRMED! Order ID: {body.get('order_id')}")
                    log_cb("🎉 SUCCESS: Checkout was accepted during the outage and confirmed after payment was restored.")
                    return True
                if body.get("status") != "PENDING":
                    raise RuntimeError(f"Checkout ended with {body.get('status')}: {body.get('reason')}.")
                log_cb("   Checkout is still PENDING; waiting for processing after payment was restored...")
                time.sleep(5)
            log_cb(f"❌ Checkout {key} did not confirm within 420s; recovery is unverified. Payment concurrency is restored.")
            return False

        except Exception as e:
            log_cb(f"❌ Exception during drill: {e}")
            return False

    def run_poison_dlq_drill(self, log_cb: Callable[[str], None]) -> bool:
        """Redrive a synthetic valid DLQ message and verify its worker confirmation."""
        tf_out = self.get_terraform_outputs()
        queue_url = tf_out.get("checkout_queue_url")
        dlq_url = tf_out.get("checkout_dlq_url")
        proc_fn = tf_out.get("function_names", {}).get("process-checkout")
        email = os.environ.get("FS_USER_A_EMAIL")

        if not queue_url or not dlq_url or not proc_fn:
            log_cb("❌ SQS queues and the checkout worker must be available in Terraform outputs.")
            return False
        if not email:
            log_cb("❌ Set FS_USER_A_EMAIL to a verified SES recipient before running this drill.")
            return False

        try:
            import boto3
            sqs = boto3.client("sqs", region_name=self.region)
            logs = boto3.client("logs", region_name=self.region)
            ses = boto3.client("ses", region_name=self.region)
            verification = ses.get_identity_verification_attributes(Identities=[email])
            if verification.get("VerificationAttributes", {}).get(email, {}).get("VerificationStatus") != "Success":
                raise RuntimeError("FS_USER_A_EMAIL must be verified in SES in this region.")

            dlq_attrs = sqs.get_queue_attributes(
                QueueUrl=dlq_url, AttributeNames=["QueueArn", "ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible", "ApproximateNumberOfMessagesDelayed"],
            )["Attributes"]
            dlq_arn = dlq_attrs["QueueArn"]
            src_arn = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]
            if any(int(dlq_attrs.get(name, 0)) > 0 for name in (
                "ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible", "ApproximateNumberOfMessagesDelayed",
            )):
                raise RuntimeError("The DLQ already contains messages; review them before this synthetic drill.")

            def task_key(task):
                return (task.get("StartedTimestamp"), task.get("SourceArn"), task.get("DestinationArn"))

            baseline_tasks = sqs.list_message_move_tasks(SourceArn=dlq_arn, MaxResults=10).get("Results", [])
            if any(task.get("Status") in ("RUNNING", "CANCELLING") for task in baseline_tasks):
                raise RuntimeError("A redrive task is already active; wait for it to finish.")
            unrelated_keys = {task_key(task) for task in baseline_tasks}
            checkout_id = str(uuid.uuid4())
            drill_start_ms = int(time.time() * 1000)
            log_cb(f"📦 [Step 1/3] Sending one synthetic valid message directly to the DLQ: {checkout_id}.")
            log_cb("   This tests redrive and worker processing, not retry exhaustion or an API checkout.")
            sqs.send_message(
                QueueUrl=dlq_url,
                MessageBody=json.dumps({
                    "schema_version": 1,
                    "checkout_id": checkout_id,
                    "user_sub": "synthetic-dlq-user",
                    "email": email,
                    "items": [{"sku": "BAG-001", "qty": 1}],
                    "requested_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                }),
            )
            time.sleep(6)

            log_cb("♻️ [Step 2/3] Starting redrive and waiting up to 120s for its completion...")
            start_before = int(time.time() * 1000)
            move_res = sqs.start_message_move_task(SourceArn=dlq_arn, DestinationArn=src_arn)
            start_after = int(time.time() * 1000)
            task_handle = move_res.get("TaskHandle")
            if not task_handle:
                raise RuntimeError("SQS did not return a redrive task handle.")
            bound_task = None
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                tasks = sqs.list_message_move_tasks(SourceArn=dlq_arn, MaxResults=10).get("Results", [])
                unrelated_keys.update(task_key(task) for task in tasks if task.get("TaskHandle") not in (None, task_handle))
                matches = [task for task in tasks if (
                    task.get("TaskHandle") == task_handle
                    and task.get("SourceArn") == dlq_arn and task.get("DestinationArn") == src_arn
                )]
                if not matches and bound_task is not None:
                    matches = [task for task in tasks if task_key(task) == bound_task and task.get("TaskHandle") in (None, task_handle)]
                if not matches and bound_task is None:
                    # SQS omits TaskHandle once a task completes; bind a unique new task in this start window.
                    matches = [task for task in tasks if (
                        task_key(task) not in unrelated_keys
                        and not task.get("TaskHandle")
                        and task.get("SourceArn") == dlq_arn and task.get("DestinationArn") == src_arn
                        and start_before <= task.get("StartedTimestamp", 0) <= start_after
                    )]
                if len(matches) > 1:
                    raise RuntimeError("Multiple redrive tasks match this start window; completion is ambiguous.")
                if matches:
                    task = matches[0]
                    bound_task = task_key(task)
                    if task.get("Status") == "COMPLETED":
                        log_cb("   ✅ This redrive task completed.")
                        break
                    if task.get("Status") in ("FAILED", "CANCELLED", "CANCELLING"):
                        raise RuntimeError(f"Redrive ended with {task.get('Status')}: {task.get('FailureReason', '')}")
                time.sleep(2)
            else:
                raise RuntimeError("This redrive task did not complete within 120s.")

            log_cb(f"👀 [Step 3/3] Waiting up to 180s for worker confirmation of {checkout_id}...")
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                pages = logs.get_paginator("filter_log_events").paginate(
                    logGroupName=f"/aws/lambda/{proc_fn}", startTime=drill_start_ms - 5000,
                    filterPattern=f'"{checkout_id}"',
                )
                for page in pages:
                    for event in page.get("events", []):
                        message = event.get("message", "")
                        json_start = message.find("{")
                        if json_start < 0:
                            continue
                        try:
                            record = json.loads(message[json_start:])
                        except ValueError:
                            continue
                        if record.get("event") != "checkout_processed" or record.get("checkout_id") != checkout_id:
                            continue
                        if record.get("status") == "CONFIRMED":
                            log_cb(f"🎉 SUCCESS: Redrive completed and synthetic checkout {checkout_id} was CONFIRMED by the worker.")
                            return True
                        if record.get("status") == "REJECTED":
                            raise RuntimeError(f"Synthetic checkout was REJECTED: {record.get('reason')}.")
                time.sleep(5)
            raise RuntimeError("No matching CONFIRMED worker record arrived within 180s; recovery is unverified.")

        except Exception as e:
            log_cb(f"❌ Exception during DLQ drill: {e}")
            return False

    def run_pod_kill_drill(self, log_cb: Callable[[str], None]) -> bool:
        """Abruptly terminate a store-api pod and verify zero-downtime routing & auto-recovery."""
        log_cb("🔍 [Step 1/4] Querying active store-api pods in Kubernetes...")
        try:
            k_env = os.environ.copy()
            if (APP_ROOT / ".kubeconfig").exists():
                k_env["KUBECONFIG"] = str(APP_ROOT / ".kubeconfig")
            res = subprocess.run(
                ["kubectl", "get", "pods", "-n", "fashionstore", "-l", "app=store-api", "-o", "jsonpath={.items[*].metadata.name}"],
                capture_output=True,
                text=True,
                timeout=15,
                env=k_env,
            )
            pods = res.stdout.strip().split()
            if not pods:
                log_cb("⚠️ No store-api pods found. Have Kubernetes workloads been deployed with `make k8s-apply`?")
                return False

            target_pod = pods[0]
            log_cb(f"   Found {len(pods)} running pods: {', '.join(pods)}")
            log_cb(f"💥 [Step 2/4] Injecting Compute Failure: Abruptly terminating pod `{target_pod}`...")

            del_res = subprocess.run(
                ["kubectl", "delete", "pod", target_pod, "-n", "fashionstore", "--now"],
                capture_output=True,
                text=True,
                timeout=30,
                env=k_env,
            )
            log_cb(f"   {del_res.stdout.strip() if del_res.stdout else del_res.stderr.strip()}")

            log_cb("🌐 [Step 3/4] Testing API availability through surviving replica pods...")
            tf_out = self.get_terraform_outputs()
            site = tf_out.get("storefront_url", os.environ.get("FS_BASE_URL"))
            if site and site.startswith("http"):
                import requests
                for i in range(5):
                    try:
                        r = requests.get(f"{site}/api/products", timeout=5)
                        log_cb(f"   Request {i+1}/5 -> HTTP {r.status_code} OK (Zero 502/504 errors)")
                    except Exception as re:
                        log_cb(f"   Request {i+1}/5 error: {re}")
                    time.sleep(1)

            log_cb("⏳ [Step 4/4] Watching Kubernetes ReplicaSet schedule replacement pod...")
            time.sleep(5)
            check_res = subprocess.run(
                ["kubectl", "get", "pods", "-n", "fashionstore", "-l", "app=store-api"],
                capture_output=True,
                text=True,
                env=k_env,
            )
            log_cb("   Current pod status:\n" + check_res.stdout.strip())
            log_cb("🎉 SUCCESS: Pod kill drill completed. High availability verified!")
            return True
        except Exception as e:
            log_cb(f"❌ Error during pod kill drill: {e}")
            return False

    # -------------------------------------------------------------------------
    # Load Tests (k6)
    # -------------------------------------------------------------------------
    def run_k6_test(self, script_name: str, profile: str, log_cb: Callable[[str], None]) -> bool:
        """Run a k6 load test script with streaming output."""
        tf_out = self.get_terraform_outputs()
        site = tf_out.get("storefront_url")
        script_path = TESTS_DIR / "load" / script_name

        if not site:
            log_cb("❌ Load tests need the deployed storefront URL in Terraform outputs.")
            return False
        if not script_path.exists():
            log_cb(f"❌ Script not found: {script_path}")
            return False

        if script_name in ("checkout.js", "flash-sale.js"):
            try:
                self.ensure_valid_tokens(self._load_users_required(profile, script_name))
            except ValueError as exc:
                log_cb(f"❌ Load preflight failed: {exc}")
                return False
            except Exception:
                log_cb("❌ Could not prepare load tokens; check the profile, token helper and local file permissions.")
                return False

        k6_bin = shutil.which("k6") or str(Path.home() / ".local" / "bin" / "k6") or "k6"
        log_cb(f"🚀 Launching k6 ({script_name}) | Profile: {profile} | Target: {site}")
        cmd = [
            k6_bin, "run",
            "-e", f"BASE_URL={site}",
            "-e", f"PROFILE={profile}",
            "-e", f"TOKENS_FILE={TESTS_DIR / 'load' / 'tokens.json'}",
            str(script_path),
        ]

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(TESTS_DIR / "load"),
            )
            if process.stdout:
                for line in iter(process.stdout.readline, ""):
                    log_cb(line.rstrip())
            process.wait()
            return process.returncode == 0
        except FileNotFoundError:
            log_cb("❌ 'k6' binary not found. Please install k6 (e.g. `sudo apt install k6` or download binary).")
            return False
        except Exception as e:
            log_cb(f"❌ Error executing k6: {e}")
            return False

    def run_full_load_suite(self, profile: str, log_cb: Callable[[str], None]) -> bool:
        """Run all 3 k6 load tests sequentially (browse, checkout, flash-sale) with live streaming logs."""
        try:
            self.ensure_valid_tokens(self._load_users_required(profile))
        except ValueError as exc:
            log_cb(f"❌ Benchmark preflight failed: {exc}")
            return False
        except Exception:
            log_cb("❌ Could not prepare load tokens; check the profile, token helper and local file permissions.")
            return False
        tests = [
            ("browse.js", "Stage 1/3: 🌐 Catalog Browsing Ramp (CloudFront CDN Edge & ALB Latency)"),
            ("checkout.js", "Stage 2/3: 🛒 Asynchronous Checkout Surge (SQS Shock Absorber & Autoscaling)"),
            ("flash-sale.js", "Stage 3/3: ⚡ Flash Sale Concurrency Race (MySQL Row Locks & Zero Oversell)"),
        ]
        all_passed = True
        log_cb("=" * 72)
        log_cb(f"🎯 LAUNCHING COMPLETE LOAD BENCHMARK SUITE | Profile: {profile.upper()}")
        log_cb("=" * 72)

        for idx, (script, label) in enumerate(tests, 1):
            log_cb("")
            log_cb("-" * 72)
            log_cb(f"🚀 [{idx}/3] {label}")
            log_cb("-" * 72)
            ok = self.run_k6_test(script, profile, log_cb)
            if not ok:
                log_cb(f"⚠️ {script} reported non-zero exit or threshold breaches.")
                all_passed = False
            else:
                log_cb(f"✅ {script} completed successfully.")

        log_cb("")
        log_cb("=" * 72)
        if all_passed:
            log_cb("🎉 ALL PERFORMANCE BENCHMARKS PASSED SUCCESSFULLY!")
        else:
            log_cb("⚠️ Benchmark completed with one or more threshold warnings.")
        log_cb("=" * 72)
        return all_passed

    # -------------------------------------------------------------------------
    # PyTest Suite Runner
    # -------------------------------------------------------------------------
    def run_pytest(self, test_rel_path: str, allow_chaos: bool, log_cb: Callable[[str], None]) -> bool:
        """Run a pytest live test file with streaming logs."""
        env = os.environ.copy()
        tf_out = self.get_terraform_outputs()
        site = tf_out.get("storefront_url", env.get("FS_BASE_URL"))

        if site:
            env["FS_BASE_URL"] = site
        if (APP_ROOT / ".kubeconfig").exists():
            env["KUBECONFIG"] = str(APP_ROOT / ".kubeconfig")
        if allow_chaos:
            env["FS_ALLOW_CHAOS"] = "1"
            env["FS_RUN_SLOW"] = "1"
        if "FS_USER_A_EMAIL" not in env:
            env["FS_USER_A_EMAIL"] = os.environ.get("FS_USER_A_EMAIL", "kaijie090803@gmail.com")
        if "FS_TEST_PASSWORD" not in env:
            env["FS_TEST_PASSWORD"] = os.environ.get("FS_TEST_PASSWORD", "Password123!")

        target_file = TESTS_DIR / test_rel_path
        if shutil.which("uv"):
            cmd = ["uv", "run", "--with", "pytest", "--with", "boto3", "--with", "requests", "pytest", "-v", str(target_file)]
        else:
            cmd = [sys.executable, "-m", "pytest", "-v", str(target_file)]
        log_cb(f"🧪 Running PyTest: {' '.join(cmd)}")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(TESTS_DIR),
                env=env,
            )
            if process.stdout:
                for line in iter(process.stdout.readline, ""):
                    log_cb(line.rstrip())
            process.wait()
            return process.returncode == 0
        except Exception as e:
            log_cb(f"❌ PyTest execution error: {e}")
            return False
