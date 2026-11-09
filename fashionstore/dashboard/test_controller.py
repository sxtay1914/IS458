import base64
import io
import json
import subprocess
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


def load_token(sub, **overrides):
    claims = {
        "sub": sub, "exp": 5000, "token_use": "access",
        "iss": "https://cognito-idp.ap-southeast-1.amazonaws.com/test-pool",
        "client_id": "test-client", "scope": "fashionstore-api/checkout.write",
        **overrides,
    }
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return f"header.{payload}.signature"


@pytest.fixture
def load_drill(monkeypatch, tmp_path):
    source = controller_module.TESTS_DIR / "load"
    load_dir = tmp_path / "load"
    (load_dir / "profiles").mkdir(parents=True)
    for profile in ("smoke", "fast-demo", "demo"):
        (load_dir / "profiles" / f"{profile}.json").write_text((source / "profiles" / f"{profile}.json").read_text())
    for script in ("browse.js", "checkout.js", "flash-sale.js"):
        (load_dir / script).touch()
    monkeypatch.setattr(controller_module, "TESTS_DIR", tmp_path)
    monkeypatch.setattr(controller_module.time, "time", lambda: 1000)
    monkeypatch.setenv("FS_TEST_PASSWORD", "secret-test-password")
    controller = Controller()
    controller._tf_outputs = {
        "storefront_url": "https://current-store.example",
        "app_config": {
            "COGNITO_ISSUER_URL": "https://cognito-idp.ap-southeast-1.amazonaws.com/test-pool",
            "COGNITO_CLIENT_ID": "test-client",
        },
    }
    refresh = Mock(side_effect=lambda args, **kwargs: SimpleNamespace(
        returncode=0, stdout=json.dumps({"access_token": load_token(args[3])}),
    ))
    monkeypatch.setattr(controller_module.subprocess, "run", refresh)
    process = SimpleNamespace(stdout=io.StringIO(""), returncode=0, wait=Mock())
    launch = Mock(return_value=process)
    monkeypatch.setattr(controller_module.subprocess, "Popen", launch)
    monkeypatch.setattr(controller_module.shutil, "which", lambda name: "/test/bin/k6")
    return SimpleNamespace(
        controller=controller, tokens_file=load_dir / "tokens.json",
        refresh=refresh, launch=launch, logs=[],
    )


def test_valid_load_token_cache_is_reused(load_drill):
    drill = load_drill
    tokens = [load_token("shopper-a"), load_token("shopper-b")]
    drill.tokens_file.write_text(json.dumps(tokens))

    drill.controller.ensure_valid_tokens(2)

    drill.refresh.assert_not_called()
    assert json.loads(drill.tokens_file.read_text()) == tokens


@pytest.mark.parametrize("invalid_second", [
    load_token("shopper-b", exp=999),
    load_token("shopper-b", exp=1500),
    load_token("shopper-b", iss="another-pool"),
    load_token("shopper-b", client_id="another-client"),
    load_token("shopper-a"),
    load_token("shopper-b", token_use="id"),
    load_token("shopper-b", scope="openid"),
    "malformed-token",
])
def test_every_cached_token_is_validated_even_when_fewer_users_are_needed(load_drill, invalid_second):
    drill = load_drill
    drill.tokens_file.write_text(json.dumps([load_token("shopper-a"), invalid_second]))

    drill.controller.ensure_valid_tokens(1)

    drill.refresh.assert_called_once()
    assert json.loads(drill.tokens_file.read_text()) == [load_token("loadtest+1@example.com")]


def test_insufficient_load_tokens_refresh_distinct_users(load_drill):
    drill = load_drill
    drill.tokens_file.write_text(json.dumps([load_token("shopper-a")]))

    drill.controller.ensure_valid_tokens(2)

    assert json.loads(drill.tokens_file.read_text()) == [
        load_token("loadtest+1@example.com"), load_token("loadtest+2@example.com"),
    ]
    assert drill.tokens_file.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("bad_token", [
    load_token("same-shopper"),
    load_token("wrong-pool", iss="another-pool"),
    load_token("expired", exp=999),
    None,
])
def test_invalid_refreshed_tokens_never_replace_cache(load_drill, bad_token):
    drill = load_drill
    original = json.dumps([load_token("old-shopper", exp=999)])
    drill.tokens_file.write_text(original)
    drill.refresh.side_effect = None
    drill.refresh.return_value = SimpleNamespace(returncode=0, stdout=json.dumps({"access_token": bad_token}))

    with pytest.raises(ValueError, match="distinct"):
        drill.controller.ensure_valid_tokens(2)

    assert drill.tokens_file.read_text() == original


@pytest.mark.parametrize(("profile", "script", "users"), [
    ("smoke", "checkout.js", 1), ("smoke", "flash-sale.js", 5),
    ("fast-demo", "checkout.js", 5), ("fast-demo", "flash-sale.js", 5),
    ("demo", "checkout.js", 15), ("demo", "flash-sale.js", 60),
])
def test_k6_prepares_enough_distinct_shoppers_for_actual_profile(load_drill, profile, script, users, monkeypatch):
    drill = load_drill
    monkeypatch.setenv("TOKENS_FILE", "/unvalidated/old-tokens.json")

    assert drill.controller.run_k6_test(script, profile, drill.logs.append)

    assert drill.refresh.call_count == users
    assert {entry.args[0][3] for entry in drill.refresh.call_args_list} == {
        f"loadtest+{i}@example.com" for i in range(1, users + 1)
    }
    assert f"TOKENS_FILE={drill.tokens_file}" in drill.launch.call_args.args[0]


@pytest.mark.parametrize("failure", ["partial", "timeout"])
def test_load_refresh_failure_stops_k6_without_exposing_credentials(load_drill, failure):
    drill = load_drill
    if failure == "timeout":
        drill.refresh.side_effect = controller_module.subprocess.TimeoutExpired(
            ["node", "get-token.mjs", "secret-test-password"], timeout=90,
        )
    else:
        def partial(args, **kwargs):
            if args[3] == "loadtest+2@example.com":
                return SimpleNamespace(returncode=1, stdout="", stderr="secret-test-password")
            return SimpleNamespace(returncode=0, stdout=json.dumps({"access_token": load_token(args[3])}))
        drill.refresh.side_effect = partial

    assert not drill.controller.run_k6_test("flash-sale.js", "smoke", drill.logs.append)

    drill.launch.assert_not_called()
    assert not drill.tokens_file.exists()
    assert "secret-test-password" not in "\n".join(drill.logs)


def test_full_benchmark_preflights_all_identities_before_starting_browse(load_drill):
    drill = load_drill
    drill.refresh.side_effect = None
    drill.refresh.return_value = SimpleNamespace(returncode=1, stdout="")

    assert not drill.controller.run_full_load_suite("demo", drill.logs.append)

    assert drill.refresh.call_count == 60
    drill.launch.assert_not_called()


@pytest.mark.parametrize("missing", ["password", "storefront_url", "COGNITO_ISSUER_URL", "COGNITO_CLIENT_ID"])
def test_load_requires_explicit_password_and_current_deployment_metadata(load_drill, missing, monkeypatch):
    drill = load_drill
    drill.tokens_file.write_text(json.dumps([load_token("shopper-a")]))
    if missing == "password":
        monkeypatch.delenv("FS_TEST_PASSWORD")
    elif missing == "storefront_url":
        drill.controller._tf_outputs.pop(missing)
        monkeypatch.setenv("FS_BASE_URL", "https://previous-deployment.example")
    else:
        drill.controller._tf_outputs["app_config"].pop(missing)

    assert not drill.controller.run_k6_test("checkout.js", "smoke", drill.logs.append)

    drill.refresh.assert_not_called()
    drill.launch.assert_not_called()


@pytest.mark.parametrize("drill_name", ["Payment Outage", "Poison DLQ Redrive", "Flash Sale", "Pod Kill", "SQS Disconnect"])
def test_clear_display_preserves_cloud_resources_and_other_history(drill_name, monkeypatch):
    controller = Controller()
    state = {
        f"last_exec_{drill_name}": {"success": True, "logs": ["Previous run"]},
        f"drill_reset_time_{drill_name}": 100,
        "last_exec_other_drill": {"success": False},
    }
    monkeypatch.setattr(controller_module.time, "time", lambda: 200)
    with patch("boto3.client") as aws_client, patch.object(
        controller_module.subprocess, "run"
    ) as run, patch.object(controller_module.subprocess, "Popen") as popen:
        controller.reset_drill_state(drill_name, state)

    assert state == {
        f"drill_reset_time_{drill_name}": 200,
        "last_exec_other_drill": {"success": False},
    }
    aws_client.assert_not_called()
    run.assert_not_called()
    popen.assert_not_called()


@pytest.fixture
def dlq_drill(monkeypatch):
    controller = Controller()
    controller._tf_outputs = {
        "checkout_queue_url": "https://sqs.example/main",
        "checkout_dlq_url": "https://sqs.example/dlq",
        "function_names": {"process-checkout": "test-worker"},
    }
    monkeypatch.setenv("FS_USER_A_EMAIL", "verified@example.com")
    checkout_id = "00000000-0000-4000-8000-000000000001"
    monkeypatch.setattr(controller_module.uuid, "uuid4", lambda: checkout_id)
    clock = [1000.0]
    monkeypatch.setattr(controller_module.time, "time", lambda: clock[0])
    monkeypatch.setattr(controller_module.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(controller_module.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    sqs, logs, ses = Mock(), Mock(), Mock()
    monkeypatch.setattr(boto3, "client", lambda service, **kwargs: {"sqs": sqs, "logs": logs, "ses": ses}[service])
    ses.get_identity_verification_attributes.return_value = {
        "VerificationAttributes": {"verified@example.com": {"VerificationStatus": "Success"}},
    }
    attributes = {
        "dlq": {"QueueArn": "dlq-arn", "ApproximateNumberOfMessages": "0", "ApproximateNumberOfMessagesNotVisible": "0"},
        "main": {"QueueArn": "main-arn", "ApproximateNumberOfMessages": "0", "ApproximateNumberOfMessagesNotVisible": "0"},
    }
    sqs.get_queue_attributes.side_effect = lambda **kwargs: {"Attributes": attributes[kwargs["QueueUrl"].rsplit("/", 1)[1]]}
    baseline = [{"StartedTimestamp": 900_000, "SourceArn": "dlq-arn", "DestinationArn": "main-arn", "Status": "COMPLETED", "ApproximateNumberOfMessagesMoved": 0}]
    started = [0]
    statuses = ["RUNNING", "COMPLETED"]
    task_overrides = {}
    extra_tasks = []

    def start_task(**kwargs):
        started[0] = int(clock[0] * 1000)
        clock[0] += 0.1
        return {"TaskHandle": "our-task"}

    def list_tasks(**kwargs):
        if not sqs.start_message_move_task.called:
            return {"Results": baseline}
        status = statuses.pop(0) if len(statuses) > 1 else statuses[0]
        task = {
            "StartedTimestamp": started[0], "SourceArn": "dlq-arn", "DestinationArn": "main-arn",
            "Status": status, "ApproximateNumberOfMessagesMoved": 1,
        }
        if status == "RUNNING":
            task["TaskHandle"] = "our-task"
        task.update(task_overrides)
        return {"Results": [task, *extra_tasks, *baseline]}

    sqs.start_message_move_task.side_effect = start_task
    sqs.list_message_move_tasks.side_effect = list_tasks
    records = [{"event": "checkout_processed", "checkout_id": checkout_id, "status": "CONFIRMED"}]

    def log_page():
        return {"events": [
            {"message": "[INFO] " + json.dumps(record), "timestamp": int(clock[0] * 1000)}
            for record in records
        ]}

    logs.get_paginator.return_value.paginate.side_effect = lambda **kwargs: [log_page()]
    logs.filter_log_events.side_effect = lambda **kwargs: log_page()
    monkeypatch.setattr(controller, "_build_time_series_df", Mock(return_value=None))
    return SimpleNamespace(
        controller=controller, sqs=sqs, logs_client=logs, ses=ses, records=records,
        attributes=attributes, baseline=baseline, statuses=statuses, task_overrides=task_overrides,
        extra_tasks=extra_tasks, started=started, checkout_id=checkout_id, clock=clock, logs=[],
    )


@pytest.mark.parametrize("fast_completion", [False, True])
def test_dlq_success_requires_its_completed_task_and_matching_confirmation(dlq_drill, fast_completion):
    drill = dlq_drill
    if fast_completion:
        drill.statuses[:] = ["COMPLETED"]  # AWS omits TaskHandle for completed tasks.

    assert drill.controller.run_poison_dlq_drill(drill.logs.append)

    body = json.loads(drill.sqs.send_message.call_args.kwargs["MessageBody"])
    assert body["checkout_id"] == drill.checkout_id
    assert body["email"] == "verified@example.com"
    assert body["items"] == [{"sku": "BAG-001", "qty": 1}]
    drill.sqs.start_message_move_task.assert_called_once_with(SourceArn="dlq-arn", DestinationArn="main-arn")
    assert drill.logs_client.get_paginator.return_value.paginate.call_args.kwargs["filterPattern"] == f'"{drill.checkout_id}"'
    drill.sqs.receive_message.assert_not_called()


@pytest.mark.parametrize("status", ["FAILED", "CANCELLED", "CANCELLING", "RUNNING"])
def test_dlq_incomplete_or_failed_task_cannot_pass(dlq_drill, status):
    drill = dlq_drill
    drill.statuses[:] = [status]

    assert not drill.controller.run_poison_dlq_drill(drill.logs.append)

    drill.logs_client.get_paginator.assert_not_called()
    assert drill.clock[0] <= 1126.2
    assert not any("SUCCESS" in line for line in drill.logs)


@pytest.mark.parametrize("mismatch", ["baseline", "wrong-handle", "wrong-destination", "outside-window"])
def test_dlq_does_not_accept_an_unrelated_completed_task(dlq_drill, mismatch):
    drill = dlq_drill
    if mismatch == "baseline":
        drill.sqs.list_message_move_tasks.side_effect = lambda **kwargs: {"Results": drill.baseline}
    elif mismatch == "wrong-handle":
        drill.task_overrides["TaskHandle"] = "another-task"
    elif mismatch == "wrong-destination":
        drill.statuses[:] = ["COMPLETED"]
        drill.task_overrides["DestinationArn"] = "another-queue"
    else:
        drill.statuses[:] = ["COMPLETED"]
        drill.task_overrides["StartedTimestamp"] = 999_999

    assert not drill.controller.run_poison_dlq_drill(drill.logs.append)

    drill.logs_client.get_paginator.assert_not_called()


def test_dlq_rejects_ambiguous_new_tasks(dlq_drill):
    drill = dlq_drill
    drill.statuses[:] = ["COMPLETED"]
    drill.extra_tasks.append({
        "StartedTimestamp": 1_006_050, "SourceArn": "dlq-arn",
        "DestinationArn": "main-arn", "Status": "COMPLETED",
    })

    assert not drill.controller.run_poison_dlq_drill(drill.logs.append)

    assert any("ambiguous" in line for line in drill.logs)
    drill.logs_client.get_paginator.assert_not_called()


@pytest.mark.parametrize("evidence", ["rejected", "wrong-checkout", "wrong-event", "missing"])
def test_dlq_never_passes_without_its_confirmed_worker_record(dlq_drill, evidence):
    drill = dlq_drill
    if evidence == "rejected":
        drill.records[0]["status"] = "REJECTED"
    elif evidence == "wrong-checkout":
        drill.records[0]["checkout_id"] = "some-other-checkout"
    elif evidence == "wrong-event":
        drill.records[0]["event"] = "checkout_received"
    else:
        drill.records.clear()

    assert not drill.controller.run_poison_dlq_drill(drill.logs.append)

    assert drill.clock[0] <= 1188.2
    assert not any("SUCCESS" in line for line in drill.logs)


@pytest.mark.parametrize("operation", ["start_message_move_task", "list_message_move_tasks", "worker_logs"])
def test_dlq_api_errors_are_failures(dlq_drill, operation):
    drill = dlq_drill
    if operation == "worker_logs":
        drill.logs_client.get_paginator.return_value.paginate.side_effect = RuntimeError("logs unavailable")
    else:
        getattr(drill.sqs, operation).side_effect = RuntimeError("SQS unavailable")

    assert not drill.controller.run_poison_dlq_drill(drill.logs.append)

    assert not any("SUCCESS" in line for line in drill.logs)


@pytest.mark.parametrize("blocker", ["missing-email", "unverified-email", "existing-messages", "active-task"])
def test_dlq_preflight_blocks_unsafe_or_unconfigured_runs(dlq_drill, blocker, monkeypatch):
    drill = dlq_drill
    if blocker == "missing-email":
        monkeypatch.delenv("FS_USER_A_EMAIL")
    elif blocker == "unverified-email":
        drill.ses.get_identity_verification_attributes.return_value = {"VerificationAttributes": {}}
    elif blocker == "existing-messages":
        drill.attributes["dlq"]["ApproximateNumberOfMessagesNotVisible"] = "1"
    else:
        drill.baseline[0]["Status"] = "RUNNING"

    assert not drill.controller.run_poison_dlq_drill(drill.logs.append)

    drill.sqs.send_message.assert_not_called()
    drill.sqs.start_message_move_task.assert_not_called()


def test_dlq_telemetry_does_not_receive_messages_or_invent_redrive_counts(dlq_drill):
    drill = dlq_drill
    drill.attributes["dlq"]["ApproximateNumberOfMessages"] = "3"
    drill.attributes["main"]["ApproximateNumberOfMessages"] = "7"

    telemetry = drill.controller.get_dlq_drill_telemetry()

    assert telemetry["available"]
    assert telemetry["summary"]["dlq_depth"] == 3
    assert telemetry["summary"]["main_depth"] == 7
    assert telemetry["summary"]["confirmed_checkouts"] == 1
    assert telemetry["summary"]["messages_moved"] == 0
    assert {entry[0] for entry in drill.sqs.method_calls} == {"get_queue_attributes", "list_message_move_tasks"}


def test_dlq_missing_task_handle_does_not_claim_redrive_success(dlq_drill):
    drill = dlq_drill
    drill.sqs.start_message_move_task.side_effect = None
    drill.sqs.start_message_move_task.return_value = {}

    assert not drill.controller.run_poison_dlq_drill(drill.logs.append)

    drill.logs_client.get_paginator.assert_not_called()
    assert not any("SUCCESS" in line for line in drill.logs)


def test_dlq_checks_all_log_pages_for_its_confirmation(dlq_drill):
    drill = dlq_drill
    paginate = drill.logs_client.get_paginator.return_value.paginate
    paginate.side_effect = None
    paginate.return_value = [
        {"events": [{"message": json.dumps({"event": "checkout_received", "checkout_id": drill.checkout_id})}]},
        {"events": [{"message": json.dumps(drill.records[0])}]},
    ]

    assert drill.controller.run_poison_dlq_drill(drill.logs.append)


def pod(name, uid, *, version="v1", ready=True, terminating=False):
    return {
        "metadata": {
            "name": name, "uid": uid, "labels": {"app": "store-api", "version": version},
            **({"deletionTimestamp": "2026-11-10T00:00:00Z"} if terminating else {}),
        },
        "status": {"phase": "Running", "conditions": [{"type": "Ready", "status": "True" if ready else "False"}]},
    }


@pytest.fixture
def pod_drill(monkeypatch):
    controller = Controller()
    controller._tf_outputs = {"storefront_url": "https://store.example"}
    drill = SimpleNamespace(
        controller=controller, clock=0, deleted=False, logs=[], api_samples=[],
        initial=[pod("v2-canary", "canary", version="v2"), pod("v1-a", "a"), pod("v1-b", "b")],
        after=[pod("v1-b", "b"), pod("v1-c", "c")],
        desired=2, recovered_desired=2, ready_after=15, fail_command=None,
    )
    monkeypatch.setattr(controller_module.time, "monotonic", lambda: drill.clock)
    monkeypatch.setattr(controller_module.time, "sleep", lambda seconds: setattr(drill, "clock", drill.clock + seconds))

    def run(cmd, **kwargs):
        args = cmd[3:]
        assert cmd[:3] == ["kubectl", "-n", "fashionstore"]
        if drill.fail_command and args[:2] == drill.fail_command:
            raise subprocess.CalledProcessError(1, cmd, stderr="kubectl failed")
        if args == ["get", "deployment", "store-api-v1", "-o", "json"]:
            result = {"spec": {"replicas": drill.recovered_desired if drill.deleted else drill.desired}}
        elif args == ["get", "pods", "-l", "app=store-api,version=v1", "-o", "json"]:
            pods = json.loads(json.dumps(drill.after if drill.deleted else drill.initial))
            if drill.deleted and drill.clock < drill.ready_after:
                for item in pods:
                    if item["metadata"]["uid"] == "c":
                        item["status"]["conditions"][0]["status"] = "False"
            result = {"items": pods}
        elif args == ["delete", "pod", "v1-a", "--now", "--wait=false"]:
            drill.deleted = True
            result = {}
        else:
            raise AssertionError(f"Unexpected kubectl call: {args}")
        return SimpleNamespace(stdout=json.dumps(result))

    def read(url, **kwargs):
        drill.api_samples.append((drill.clock, drill.deleted))
        return Mock(status_code=200, json=Mock(return_value=[]))

    drill.run = Mock(side_effect=run)
    drill.read = Mock(side_effect=read)
    monkeypatch.setattr(controller_module.subprocess, "run", drill.run)
    monkeypatch.setattr(requests, "get", drill.read)
    return drill


def test_pod_drill_checks_v1_replacement_and_samples_during_recovery(pod_drill):
    drill = pod_drill

    assert drill.controller.run_pod_kill_drill(drill.logs.append)

    assert drill.deleted
    assert any(deleted and when < drill.ready_after for when, deleted in drill.api_samples)
    assert sum(deleted for _, deleted in drill.api_samples) >= 5
    assert any("v1-c is Ready" in line for line in drill.logs)
    assert all(entry.kwargs["check"] and entry.kwargs["timeout"] == 15 for entry in drill.run.call_args_list)
    assert all(entry == call("https://store.example/api/products", timeout=5, allow_redirects=False)
               for entry in drill.read.call_args_list)
    assert len([entry for entry in drill.run.call_args_list if entry.args[0][3] == "delete"]) == 1


@pytest.mark.parametrize("site", [None, "http://store.example", "https:///missing-host", "https://user:secret@store.example"])
def test_pod_drill_requires_deployed_https_url_before_deletion(pod_drill, monkeypatch, site):
    drill = pod_drill
    drill.controller._tf_outputs["storefront_url"] = site
    monkeypatch.setenv("FS_BASE_URL", "https://fallback.example")

    assert not drill.controller.run_pod_kill_drill(drill.logs.append)

    drill.run.assert_not_called()
    drill.read.assert_not_called()


@pytest.mark.parametrize("blocker", ["single-v1", "not-ready", "terminating", "desired-one"])
def test_pod_drill_requires_two_ready_v1_pods_before_deletion(pod_drill, blocker):
    drill = pod_drill
    if blocker == "single-v1":
        drill.initial.pop()
    elif blocker == "not-ready":
        drill.initial[-1] = pod("v1-b", "b", ready=False)
    elif blocker == "terminating":
        drill.initial[-1] = pod("v1-b", "b", terminating=True)
    else:
        drill.desired = 1

    assert not drill.controller.run_pod_kill_drill(drill.logs.append)

    assert not drill.deleted


@pytest.mark.parametrize("command", [["get", "deployment"], ["get", "pods"], ["delete", "pod"]])
def test_pod_drill_checks_kubectl_failures(pod_drill, command):
    drill = pod_drill
    drill.fail_command = command

    assert not drill.controller.run_pod_kill_drill(drill.logs.append)

    assert not drill.deleted
    assert not any("SUCCESS" in line for line in drill.logs)


@pytest.mark.parametrize("failure", ["http", "redirect", "network", "not-products", "json"])
@pytest.mark.parametrize("after_delete", [False, True])
def test_pod_drill_rejects_failed_api_samples(pod_drill, failure, after_delete):
    drill = pod_drill
    response = Mock(status_code=200, json=Mock(return_value=[]))
    if failure == "http":
        response.status_code = 503
    elif failure == "redirect":
        response.status_code = 302
    elif failure == "network":
        response = requests.ConnectionError("API unreachable")
    elif failure == "not-products":
        response.json.return_value = {"message": "not a product list"}
    else:
        response.json.side_effect = ValueError("invalid JSON")
    drill.read.side_effect = ([Mock(status_code=200, json=Mock(return_value=[]))] if after_delete else []) + [response]

    assert not drill.controller.run_pod_kill_drill(drill.logs.append)

    assert drill.deleted == after_delete
    assert not any("SUCCESS" in line for line in drill.logs)


@pytest.mark.parametrize("missing", ["old-pod-remains", "same-uid", "same-name", "old-pending", "only-v2", "desired-capacity", "not-ready"])
def test_pod_drill_never_passes_without_new_ready_identity_and_capacity(pod_drill, missing):
    drill = pod_drill
    if missing == "old-pod-remains":
        drill.after.append(pod("v1-a", "a", terminating=True))
    elif missing == "same-uid":
        drill.after[-1] = pod("v1-c", "a")
    elif missing == "same-name":
        drill.after[-1] = pod("v1-a", "c")
    elif missing == "old-pending":
        drill.initial.append(pod("v1-c", "c", ready=False))
    elif missing == "only-v2":
        drill.after[-1] = pod("v2-new", "c", version="v2")
    elif missing == "desired-capacity":
        drill.recovered_desired = 3
    else:
        drill.ready_after = 600

    assert not drill.controller.run_pod_kill_drill(drill.logs.append)

    assert drill.clock == 300
    assert not any("SUCCESS" in line for line in drill.logs)


def test_pod_drill_accepts_current_scaled_up_ready_capacity(pod_drill):
    drill = pod_drill
    drill.recovered_desired = 3
    drill.after.append(pod("v1-d", "d"))

    assert drill.controller.run_pod_kill_drill(drill.logs.append)

    assert any("3/3 desired" in line for line in drill.logs)


def test_pod_drill_subprocess_timeout_is_not_success(pod_drill):
    drill = pod_drill
    drill.run.side_effect = subprocess.TimeoutExpired("kubectl", 15)

    assert not drill.controller.run_pod_kill_drill(drill.logs.append)

    assert not drill.deleted
    assert not any("SUCCESS" in line for line in drill.logs)
