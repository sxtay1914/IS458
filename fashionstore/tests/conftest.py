"""Shared fixtures for the live tests (tests/security, tests/correctness, tests/failure).

They run against a deployed demo stack and are skipped when FS_BASE_URL is unset.

  FS_BASE_URL         https://dxxxx.cloudfront.net (terraform output storefront_url)
  FS_USER_A_EMAIL     test shopper A   } created with scripts/create-test-users.sh
  FS_USER_B_EMAIL     test shopper B   }
  FS_TEST_PASSWORD    their password
  FS_DECLINE_EMAIL    optional: an address containing "+decline"
  FS_ALLOW_CHAOS=1    run tests marked chaos (they change, then restore, the stack)
  FS_RUN_SLOW=1       run tests marked slow

Tokens come from tests/e2e/tools/get-token.mjs (hosted UI + PKCE), so
`cd tests/e2e && npm install` first.
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import time
import uuid
from functools import lru_cache
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "infra" / "terraform" / "environments" / "demo"
REGION = os.environ.get("AWS_REGION", "ap-southeast-1")


def pytest_collection_modifyitems(config, items):
    for item in items:
        if not os.environ.get("FS_BASE_URL"):
            item.add_marker(pytest.mark.skip(reason="FS_BASE_URL not set (live test)"))
        if "chaos" in item.keywords and os.environ.get("FS_ALLOW_CHAOS") != "1":
            item.add_marker(pytest.mark.skip(reason="set FS_ALLOW_CHAOS=1 to run"))
        if "slow" in item.keywords and os.environ.get("FS_RUN_SLOW") != "1":
            item.add_marker(pytest.mark.skip(reason="set FS_RUN_SLOW=1 to run"))


def need(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"{name} not set")
    return value


@lru_cache(maxsize=None)
def tf_output(name: str):
    out = subprocess.run(["terraform", f"-chdir={DEMO_DIR}", "output", "-json", name],
                         check=True, capture_output=True, text=True).stdout
    return json.loads(out)


@lru_cache(maxsize=None)
def get_tokens(email: str, password: str) -> dict:
    out = subprocess.run(
        ["node", str(ROOT / "tests" / "e2e" / "tools" / "get-token.mjs"), os.environ["FS_BASE_URL"], email, password],
        check=True, capture_output=True, text=True, timeout=90,
    ).stdout
    return json.loads(out)


def jwt_claims(token: str) -> dict:
    part = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))


class Api:
    def __init__(self, base: str, token: str | None = None):
        self.base = base.rstrip("/") + "/api"
        self.s = requests.Session()
        if token:
            self.s.headers["Authorization"] = f"Bearer {token}"

    def get(self, path, **kw):
        return self.s.get(self.base + path, timeout=15, **kw)

    def put(self, path, body, **kw):
        return self.s.put(self.base + path, json=body, timeout=15, **kw)

    def post(self, path, headers=None, **kw):
        return self.s.post(self.base + path, headers=headers or {}, timeout=15, **kw)

    # helpers
    def set_cart(self, items):
        r = self.put("/cart", {"items": items})
        assert r.status_code == 200, r.text
        return r.json()

    def checkout(self, key: str | None = None):
        return self.post("/checkouts", headers={"Idempotency-Key": key or str(uuid.uuid4())})

    def wait_for_outcome(self, checkout_id: str, timeout: float = 180) -> dict:
        deadline = time.time() + timeout
        delay = 1.0
        while time.time() < deadline:
            r = self.get(f"/checkouts/{checkout_id}")
            assert r.status_code == 200, r.text
            body = r.json()
            if body["status"] != "PENDING":
                return body
            time.sleep(delay)
            delay = min(delay * 1.5, 10)
        raise AssertionError(f"checkout {checkout_id} still PENDING after {timeout}s")


@pytest.fixture(scope="session")
def base_url() -> str:
    return need("FS_BASE_URL").rstrip("/")


@pytest.fixture(scope="session")
def anon(base_url) -> Api:
    return Api(base_url)


def _shopper(base_url, email_var):
    tokens = get_tokens(need(email_var), need("FS_TEST_PASSWORD"))
    api = Api(base_url, tokens["access_token"])
    api.tokens = tokens
    api.sub = jwt_claims(tokens["access_token"])["sub"]
    api.email = os.environ[email_var]
    return api


@pytest.fixture(scope="session")
def shopper_a(base_url) -> Api:
    return _shopper(base_url, "FS_USER_A_EMAIL")


@pytest.fixture(scope="session")
def shopper_b(base_url) -> Api:
    return _shopper(base_url, "FS_USER_B_EMAIL")


@pytest.fixture(scope="session")
def aws():
    import boto3
    return boto3.session.Session(region_name=REGION)
