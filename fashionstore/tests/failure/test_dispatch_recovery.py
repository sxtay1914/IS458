"""If store-api cannot reach SQS, the checkout stays PENDING and the reconciler sends it later."""
import json
import subprocess
import time
import uuid

import pytest

NS = "fashionstore"
DEPLOYMENTS = ["store-api-v1", "store-api-v2"]


def kubectl(*args):
    return subprocess.run(["kubectl", "-n", NS, *args], check=True, capture_output=True, text=True).stdout


def queue_url_env(deploy):
    spec = json.loads(kubectl("get", "deployment", deploy, "-o", "json"))
    for e in spec["spec"]["template"]["spec"]["containers"][0].get("env", []):
        if e["name"] == "CHECKOUT_QUEUE_URL":
            return e.get("value")
    return None


def set_queue_url(value):
    for d in DEPLOYMENTS:
        kubectl("set", "env", f"deployment/{d}", f"CHECKOUT_QUEUE_URL{'=' + value if value else '-'}")
    for d in DEPLOYMENTS:
        kubectl("rollout", "status", f"deployment/{d}", "--timeout=300s")


@pytest.mark.chaos
def test_reconciler_dispatches_checkouts_that_missed_the_queue(shopper_a):
    original = {d: queue_url_env(d) for d in DEPLOYMENTS}
    assert len(set(original.values())) == 1, original
    # The queue URL normally comes from the app-config ConfigMap (envFrom); an
    # explicit env var overrides it, and removing it restores the ConfigMap value.
    bogus = "https://sqs.ap-southeast-1.amazonaws.com/000000000000/does-not-exist"
    set_queue_url(bogus)
    try:
        shopper_a.set_cart([{"sku": "SHO-001-38", "qty": 1}])
        key = str(uuid.uuid4())
        assert shopper_a.checkout(key).status_code == 202      # accepted even though SQS failed
        time.sleep(40)
        assert shopper_a.get(f"/checkouts/{key}").json()["status"] == "PENDING"
    finally:
        set_queue_url(original[DEPLOYMENTS[0]])
    # Reconciler runs every 15 s for rows older than 30 s.
    assert shopper_a.wait_for_outcome(key, timeout=300)["status"] == "CONFIRMED"
