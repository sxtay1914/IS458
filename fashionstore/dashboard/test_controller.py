import base64
import io
import json
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
