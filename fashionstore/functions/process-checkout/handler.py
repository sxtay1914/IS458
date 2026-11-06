"""process-checkout: SQS checkout-requests -> one RDS transaction -> SNS checkout-status.

Uses partial batch responses (ReportBatchItemFailures), so only failed messages
are retried. After maxReceiveCount failures a message moves to checkout-dlq.
"""
from __future__ import annotations

import json
import logging
import os

import boto3

from fashionstore_common import db
from repository import CheckoutRepository
from service import CheckoutService, InvalidMessage, PaymentResult

log = logging.getLogger()
log.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

_clients: dict = {}


def _client(name: str):
    if name not in _clients:
        _clients[name] = boto3.client(name)
    return _clients[name]


class LambdaPaymentClient:
    def __init__(self, function_name: str, lambda_client=None):
        self.function_name = function_name
        self.client = lambda_client or _client("lambda")

    def authorize(self, checkout_id: str, amount_cents: int, email: str) -> PaymentResult:
        resp = self.client.invoke(
            FunctionName=self.function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps({"checkout_id": checkout_id, "amount_cents": amount_cents, "email": email}).encode(),
        )
        body = json.loads(resp["Payload"].read())
        if resp.get("FunctionError"):
            raise RuntimeError(f"payment-api failed: {body}")
        return PaymentResult(bool(body["approved"]), body["payment_ref"], body.get("reason"))


class SnsPublisher:
    def __init__(self, topic_arn: str, sns_client=None):
        self.topic_arn = topic_arn
        self.client = sns_client or _client("sns")

    def publish(self, event: dict) -> None:
        self.client.publish(
            TopicArn=self.topic_arn,
            Message=json.dumps(event),
            MessageAttributes={"status": {"DataType": "String", "StringValue": event["status"]}},
        )


def build_service() -> CheckoutService:
    return CheckoutService(
        repo=CheckoutRepository(db.get_connection()),
        payment=LambdaPaymentClient(os.environ["PAYMENT_FUNCTION_NAME"]),
        publisher=SnsPublisher(os.environ["STATUS_TOPIC_ARN"]),
    )


def process_records(records: list[dict], service: CheckoutService) -> dict:
    failures = []
    for record in records:
        message_id = record.get("messageId")
        try:
            outcome = service.process(json.loads(record["body"]))
            log.info(json.dumps({"event": "checkout_processed", "message_id": message_id,
                                 "checkout_id": outcome.checkout_id, "status": outcome.status,
                                 "reason": outcome.reason}))
        except (InvalidMessage, json.JSONDecodeError) as exc:
            log.error(json.dumps({"event": "checkout_invalid", "message_id": message_id, "error": str(exc)}))
            failures.append({"itemIdentifier": message_id})
        except Exception:  # noqa: BLE001 - every other failure is retried by SQS
            log.exception("checkout_failed message_id=%s", message_id)
            failures.append({"itemIdentifier": message_id})
    return {"batchItemFailures": failures}


def lambda_handler(event, context):
    return process_records(event.get("Records", []), build_service())
