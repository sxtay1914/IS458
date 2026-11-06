"""process-checkout failures are retried by SQS, and poison messages end in the DLQ."""
import time
import uuid

import pytest

from conftest import tf_output


def dlq_depth(sqs, url):
    a = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["ApproximateNumberOfMessages"])
    return int(a["Attributes"]["ApproximateNumberOfMessages"])


@pytest.mark.chaos
def test_checkout_survives_payment_outage(aws, shopper_a):
    """Throttle payment-api to zero, place a checkout, restore: SQS redelivery completes it."""
    lam = aws.client("lambda")
    fn = tf_output("function_names")["payment-api"]
    previous = lam.get_function_concurrency(FunctionName=fn).get("ReservedConcurrentExecutions")
    lam.put_function_concurrency(FunctionName=fn, ReservedConcurrentExecutions=0)
    try:
        shopper_a.set_cart([{"sku": "TOP-001-S", "qty": 1}])
        key = str(uuid.uuid4())
        assert shopper_a.checkout(key).status_code == 202
        time.sleep(45)
        assert shopper_a.get(f"/checkouts/{key}").json()["status"] == "PENDING"
    finally:
        if previous is None:
            lam.delete_function_concurrency(FunctionName=fn)
        else:
            lam.put_function_concurrency(FunctionName=fn, ReservedConcurrentExecutions=previous)
    # Next delivery after the 180 s visibility timeout succeeds.
    assert shopper_a.wait_for_outcome(key, timeout=420)["status"] == "CONFIRMED"


@pytest.mark.slow
def test_poison_message_lands_in_dlq_after_five_receives(aws):
    sqs = aws.client("sqs")
    queue_url, dlq_url = tf_output("checkout_queue_url"), tf_output("checkout_dlq_url")
    before = dlq_depth(sqs, dlq_url)
    sqs.send_message(QueueUrl=queue_url, MessageBody='{"schema_version": 99, "poison": "%s"}' % uuid.uuid4())
    # 5 receives x 180 s visibility = about 15 minutes.
    deadline = time.time() + 20 * 60
    while time.time() < deadline:
        if dlq_depth(sqs, dlq_url) > before:
            return
        time.sleep(30)
    raise AssertionError("poison message never reached the DLQ")
