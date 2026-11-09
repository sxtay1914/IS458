import importlib.util
import subprocess
from pathlib import Path
from unittest.mock import Mock, call

import pytest


@pytest.fixture
def drill():
    path = Path(__file__).resolve().parents[1] / "tests/failure/test_dispatch_recovery.py"
    spec = importlib.util.spec_from_file_location("dispatch_recovery", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("failed_stage", ["set", "rollout"])
@pytest.mark.parametrize("original", [None, "https://original-queue.example"])
def test_partial_injection_failure_restores_both_deployments(drill, monkeypatch, failed_stage, original):
    monkeypatch.setattr(drill, "queue_url_env", lambda deploy: original)
    injection_failed = False

    def run(*args, **kwargs):
        nonlocal injection_failed
        if not injection_failed and args[0] == failed_stage and args[2] == "deployment/store-api-v2":
            injection_failed = True
            raise subprocess.CalledProcessError(1, args)

    kubectl = Mock(side_effect=run)
    monkeypatch.setattr(drill, "kubectl", kubectl)
    shopper = Mock()

    with pytest.raises(subprocess.CalledProcessError):
        drill.test_reconciler_dispatches_checkouts_that_missed_the_queue(shopper)

    restored_value = f"CHECKOUT_QUEUE_URL{'=' + original if original else '-'}"
    assert kubectl.call_args_list[-4:] == [
        call("set", "env", "deployment/store-api-v1", restored_value),
        call("set", "env", "deployment/store-api-v2", restored_value),
        call("rollout", "status", "deployment/store-api-v1", "--timeout=300s", timeout=310),
        call("rollout", "status", "deployment/store-api-v2", "--timeout=300s", timeout=310),
    ]
    shopper.set_cart.assert_not_called()
    shopper.wait_for_outcome.assert_not_called()


@pytest.mark.parametrize("failed_stage", ["set", "rollout"])
@pytest.mark.parametrize("failure", [subprocess.TimeoutExpired("kubectl", 30), KeyboardInterrupt()])
def test_cleanup_attempts_every_deployment_and_propagates_failure(drill, monkeypatch, failed_stage, failure):
    def run(*args, **kwargs):
        if args[0] == failed_stage and args[2] == "deployment/store-api-v1":
            raise failure

    kubectl = Mock(side_effect=run)
    monkeypatch.setattr(drill, "kubectl", kubectl)

    with pytest.raises(type(failure)):
        drill.restore_queue_urls({"store-api-v1": None, "store-api-v2": "https://original-queue.example"})

    assert kubectl.call_args_list == [
        call("set", "env", "deployment/store-api-v1", "CHECKOUT_QUEUE_URL-"),
        call("set", "env", "deployment/store-api-v2", "CHECKOUT_QUEUE_URL=https://original-queue.example"),
        call("rollout", "status", "deployment/store-api-v1", "--timeout=300s", timeout=310),
        call("rollout", "status", "deployment/store-api-v2", "--timeout=300s", timeout=310),
    ]


def test_kubectl_has_bounded_subprocess_timeouts(drill, monkeypatch):
    run = Mock(return_value=Mock(stdout="ok"))
    monkeypatch.setattr(drill.subprocess, "run", run)

    assert drill.kubectl("get", "pods") == "ok"
    drill.set_queue_url("https://queue.example")

    assert [entry.kwargs["timeout"] for entry in run.call_args_list] == [30, 30, 30, 310, 310]
    assert all(entry.kwargs["check"] for entry in run.call_args_list)
