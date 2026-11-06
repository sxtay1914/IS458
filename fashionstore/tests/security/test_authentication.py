"""Every endpoint except the catalogue needs a valid Cognito *access* token."""
import uuid

import pytest

PROTECTED = [
    ("GET", "/cart"), ("PUT", "/cart"), ("POST", "/checkouts"),
    ("GET", f"/checkouts/{uuid.uuid4()}"), ("GET", "/orders"), ("GET", "/orders/1"),
]


def call(api, method, path):
    if method == "PUT":
        return api.put(path, {"items": []})
    if method == "POST":
        return api.post(path, headers={"Idempotency-Key": str(uuid.uuid4())})
    return api.get(path)


def test_catalogue_and_version_are_public(anon):
    assert anon.get("/products").status_code == 200
    assert anon.get("/products/DRS-001-M").status_code == 200
    assert anon.get("/version").json()["version"] in ("v1", "v2")


@pytest.mark.parametrize("method,path", PROTECTED)
def test_no_token_is_rejected(anon, method, path):
    assert call(anon, method, path).status_code == 401


@pytest.mark.parametrize("method,path", PROTECTED)
def test_garbage_token_is_rejected(base_url, method, path):
    from conftest import Api
    assert call(Api(base_url, "not.a.jwt"), method, path).status_code == 401


def test_tampered_signature_is_rejected(base_url, shopper_a):
    from conftest import Api
    h, p, s = shopper_a.tokens["access_token"].split(".")
    forged = f"{h}.{p}.{s[:-4]}AAAA"
    assert Api(base_url, forged).get("/cart").status_code == 401


def test_id_token_is_not_an_access_token(base_url, shopper_a):
    """The API checks token_use=access; an ID token must not work as a bearer token."""
    from conftest import Api
    assert Api(base_url, shopper_a.tokens["id_token"]).get("/cart").status_code == 401


def test_real_access_token_is_accepted(shopper_a):
    assert shopper_a.get("/cart").status_code == 200
    assert shopper_a.get("/orders").status_code == 200


def test_errors_carry_a_correlation_id(shopper_a):
    r = shopper_a.post("/checkouts", headers={"Idempotency-Key": "not-a-uuid"})
    assert r.status_code == 400
    assert r.json()["error"] == "INVALID_ID"
    assert r.json()["correlation_id"]
