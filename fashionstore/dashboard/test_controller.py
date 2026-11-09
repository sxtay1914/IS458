from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import boto3
import pytest
import requests
from botocore.exceptions import ClientError
from botocore.stub import Stubber

import controller as controller_module
from controller import TestController as Controller


def test_canary_update_uses_supported_elbv2_operation():
    client = boto3.client(
        "elbv2", region_name="ap-southeast-1",
        aws_access_key_id="test", aws_secret_access_key="test",
    )
    controller = Controller()
    controller._tf_outputs = {"target_group_arns": {"v1": "target-v1", "v2": "target-v2"}}
    expected = {
        "RuleArn": "listener-rule",
        "Actions": [{
            "Type": "forward",
            "ForwardConfig": {
                "TargetGroups": [
                    {"TargetGroupArn": "target-v1", "Weight": 80},
                    {"TargetGroupArn": "target-v2", "Weight": 20},
                ],
                "TargetGroupStickinessConfig": {"Enabled": False, "DurationSeconds": 1},
            },
        }],
    }
    with Stubber(client) as stubber:
        stubber.add_response("modify_rule", {"Rules": []}, expected)
        with patch("boto3.client", return_value=client), patch.object(
            controller, "get_canary_weights", return_value={"rule_arn": "listener-rule"}
        ):
            result = controller.set_canary_weights(80, 20)
        assert result["success"], result["message"]
        stubber.assert_no_pending_responses()


@pytest.fixture
def payment_drill(monkeypatch):
    controller = Controller(region="ap-southeast-1")
    controller._tf_outputs = {
        "storefront_url": "https://store.example",
        "function_names": {"payment-api": "test-payment"},
    }
    monkeypatch.setenv("FS_USER_A_EMAIL", "drill@example.com")
    monkeypatch.setenv("FS_TEST_PASSWORD", "test-password")
    token = Mock(return_value=SimpleNamespace(returncode=0, stdout='{"access_token":"test-token"}'))
    monkeypatch.setattr(controller_module.subprocess, "run", token)
    lam = Mock()
    lam.get_function_concurrency.return_value = {}
    lam.invoke.side_effect = ClientError({"Error": {"Code": "TooManyRequestsException"}}, "Invoke")
    aws_client = Mock(return_value=lam)
    monkeypatch.setattr(boto3, "client", aws_client)
    clock = [0]
    monkeypatch.setattr(controller_module.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(controller_module.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    product = Mock(status_code=200)
    product.json.return_value = {"stock": 40}
    cart = Mock(return_value=Mock(status_code=200))
    checkout = Mock(return_value=Mock(status_code=202))
    monkeypatch.setattr(requests, "put", cart)
    monkeypatch.setattr(requests, "post", checkout)
    outcome = {"status": "CONFIRMED", "order_id": 1}
    confirm_after = [0]

    def read_status(url, **kwargs):
        if url.endswith("/products/BAG-001"):
            return product
        response = Mock(status_code=200)
        restored = lam.delete_function_concurrency.called or lam.put_function_concurrency.call_count > 1
        response.json.return_value = outcome if restored and clock[0] >= confirm_after[0] else {"status": "PENDING"}
        return response

    read = Mock(side_effect=read_status)
    monkeypatch.setattr(requests, "get", read)
    return SimpleNamespace(
        controller=controller, lam=lam, aws_client=aws_client, token=token,
        product=product, cart=cart, checkout=checkout, read=read, outcome=outcome,
        confirm_after=confirm_after, clock=clock, logs=[],
    )


@pytest.mark.parametrize("previous", [None, 5])
def test_payment_drill_restores_original_concurrency_and_waits_for_sqs(payment_drill, previous):
    drill = payment_drill
    drill.lam.get_function_concurrency.return_value = {} if previous is None else {"ReservedConcurrentExecutions": previous}
    drill.confirm_after[0] = 250

    assert drill.controller.run_payment_outage_drill(drill.logs.append)

    assert drill.clock[0] >= 250  # Confirmation after the 180-second SQS visibility timeout.
    calls = [call(FunctionName="test-payment", ReservedConcurrentExecutions=0)]
    if previous is None:
        drill.lam.delete_function_concurrency.assert_called_once_with(FunctionName="test-payment")
    else:
        calls.append(call(FunctionName="test-payment", ReservedConcurrentExecutions=previous))
        drill.lam.delete_function_concurrency.assert_not_called()
    assert drill.lam.put_function_concurrency.call_args_list == calls
    drill.cart.assert_called_once_with(
        "https://store.example/api/cart", json={"items": [{"sku": "BAG-001", "qty": 1}]},
        headers={"Authorization": "Bearer test-token"}, timeout=15,
    )
    assert drill.aws_client.call_args_list == [call("lambda", region_name="ap-southeast-1")]


@pytest.mark.parametrize("previous", [None, 5])
@pytest.mark.parametrize("error", [requests.ConnectionError("checkout unavailable"), KeyboardInterrupt()])
def test_payment_drill_restores_after_error_or_interruption(payment_drill, previous, error):
    drill = payment_drill
    drill.lam.get_function_concurrency.return_value = {} if previous is None else {"ReservedConcurrentExecutions": previous}
    drill.checkout.side_effect = error

    if isinstance(error, KeyboardInterrupt):
        with pytest.raises(KeyboardInterrupt):
            drill.controller.run_payment_outage_drill(drill.logs.append)
    else:
        assert not drill.controller.run_payment_outage_drill(drill.logs.append)

    if previous is None:
        drill.lam.delete_function_concurrency.assert_called_once_with(FunctionName="test-payment")
    else:
        assert drill.lam.put_function_concurrency.call_args == call(FunctionName="test-payment", ReservedConcurrentExecutions=previous)
    assert not any("SUCCESS" in line for line in drill.logs)


@pytest.mark.parametrize("status", ["REJECTED", "PENDING"])
def test_payment_drill_cannot_pass_without_confirmation(payment_drill, status):
    drill = payment_drill
    drill.outcome["status"] = status

    assert not drill.controller.run_payment_outage_drill(drill.logs.append)

    drill.lam.delete_function_concurrency.assert_called_once()
    assert drill.clock[0] <= 48 + 420
    assert not any("SUCCESS" in line for line in drill.logs)


@pytest.mark.parametrize("setup_failure", ["token", "stock", "cart"])
def test_payment_drill_validates_setup_before_disabling_payment(payment_drill, setup_failure):
    drill = payment_drill
    if setup_failure == "token":
        drill.token.return_value.returncode = 1
    elif setup_failure == "stock":
        drill.product.json.return_value = {"stock": 0}
    else:
        drill.cart.return_value.status_code = 401

    assert not drill.controller.run_payment_outage_drill(drill.logs.append)

    drill.lam.put_function_concurrency.assert_not_called()
    drill.checkout.assert_not_called()


def test_payment_drill_reports_failed_restore(payment_drill):
    drill = payment_drill
    drill.lam.delete_function_concurrency.side_effect = RuntimeError("restore unavailable")

    assert not drill.controller.run_payment_outage_drill(drill.logs.append)

    assert any("RESTORE FAILED" in line for line in drill.logs)
    assert not any("SUCCESS" in line for line in drill.logs)


def test_payment_drill_restores_when_throttle_request_times_out(payment_drill):
    drill = payment_drill
    drill.lam.put_function_concurrency.side_effect = TimeoutError("response lost after setting concurrency")

    assert not drill.controller.run_payment_outage_drill(drill.logs.append)

    drill.lam.delete_function_concurrency.assert_called_once_with(FunctionName="test-payment")
    drill.checkout.assert_not_called()


def test_payment_drill_restores_before_logging_after_ui_interruption(payment_drill):
    drill = payment_drill

    def interrupted_log(message):
        if drill.lam.put_function_concurrency.called:
            raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        drill.controller.run_payment_outage_drill(interrupted_log)

    drill.lam.delete_function_concurrency.assert_called_once_with(FunctionName="test-payment")
