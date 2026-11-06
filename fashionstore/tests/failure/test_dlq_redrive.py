"""A valid checkout parked in the DLQ is processed after a redrive."""
import datetime
import json
import time
import uuid

from conftest import tf_output


def test_redriven_message_becomes_an_order(aws, shopper_a):
    sqs = aws.client("sqs")
    dlq_url, queue_url = tf_output("checkout_dlq_url"), tf_output("checkout_queue_url")
    dlq_arn = sqs.get_queue_attributes(QueueUrl=dlq_url, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]
    src_arn = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]

    cid = str(uuid.uuid4())
    sqs.send_message(QueueUrl=dlq_url, MessageBody=json.dumps({
        "schema_version": 1, "checkout_id": cid, "user_sub": shopper_a.sub, "email": shopper_a.email,
        "items": [{"sku": "BTM-002-S", "qty": 1}],
        "requested_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }))
    time.sleep(5)
    sqs.start_message_move_task(SourceArn=dlq_arn, DestinationArn=src_arn)

    deadline = time.time() + 180
    while time.time() < deadline:
        if any(o["checkout_id"] == cid for o in shopper_a.get("/orders").json()):
            return
        time.sleep(5)
    raise AssertionError(f"redriven checkout {cid} never became an order")
