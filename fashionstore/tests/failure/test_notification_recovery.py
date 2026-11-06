"""A notifier outage delays the email but never loses or duplicates it."""
import json
import time
import uuid

import pytest

from conftest import tf_output


def notifier_results(aws, fn, checkout_id, since_ms):
    logs = aws.client("logs")
    events = logs.filter_log_events(logGroupName=f"/aws/lambda/{fn}", startTime=since_ms,
                                    filterPattern=f'"{checkout_id}"').get("events", [])
    out = []
    for e in events:
        try:
            body = json.loads(e["message"][e["message"].index("{"):])
        except ValueError:
            continue
        if body.get("event") == "notification":
            out.append(body["result"])
    return out


@pytest.mark.chaos
def test_email_is_sent_once_after_notifier_recovers(aws, shopper_a):
    lam = aws.client("lambda")
    fn = tf_output("function_names")["notifier"]
    since = int(time.time() * 1000)
    previous = lam.get_function_concurrency(FunctionName=fn).get("ReservedConcurrentExecutions")
    lam.put_function_concurrency(FunctionName=fn, ReservedConcurrentExecutions=0)
    try:
        shopper_a.set_cart([{"sku": "TOP-001-S", "qty": 1}])
        key = str(uuid.uuid4())
        shopper_a.checkout(key)
        assert shopper_a.wait_for_outcome(key)["status"] == "CONFIRMED"   # orders don't wait for email
        time.sleep(30)
        assert notifier_results(aws, fn, key, since) == []
    finally:
        if previous is None:
            lam.delete_function_concurrency(FunctionName=fn)
        else:
            lam.put_function_concurrency(FunctionName=fn, ReservedConcurrentExecutions=previous)

    # Async invokes are retried with backoff (up to minutes); the reconciler also republishes.
    deadline = time.time() + 15 * 60
    while time.time() < deadline:
        results = notifier_results(aws, fn, key, since)
        if "SENT" in results:
            assert results.count("SENT") == 1, results
            return
        time.sleep(30)
    raise AssertionError("no SENT notification within 15 minutes")
