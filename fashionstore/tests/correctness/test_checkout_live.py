"""The checkout path end to end on the deployed stack."""
import collections
import os
import uuid

import pytest


def stock(api, sku):
    return api.get(f"/products/{sku}").json()["stock"]


def test_checkout_confirms_decrements_stock_and_clears_cart(shopper_a):
    before = stock(shopper_a, "DRS-001-M")
    shopper_a.set_cart([{"sku": "DRS-001-M", "qty": 1}])
    key = str(uuid.uuid4())
    r = shopper_a.checkout(key)
    assert r.status_code == 202
    assert r.headers["Location"].endswith(f"/api/checkouts/{key}")
    assert r.json()["status"] == "PENDING"
    assert shopper_a.get("/cart").json()["items"] == []

    outcome = shopper_a.wait_for_outcome(key)
    assert outcome["status"] == "CONFIRMED", outcome
    assert stock(shopper_a, "DRS-001-M") <= before - 1
    order = shopper_a.get(f"/orders/{outcome['order_id']}").json()
    assert order["checkout_id"] == key
    assert order["items"][0]["sku"] == "DRS-001-M"


def test_retry_with_same_key_returns_same_checkout_and_one_order(shopper_a):
    shopper_a.set_cart([{"sku": "TOP-002-M", "qty": 1}])
    key = str(uuid.uuid4())
    first = shopper_a.checkout(key)
    second = shopper_a.checkout(key)          # e.g. the shopper double-clicked
    assert first.status_code == second.status_code == 202
    assert first.json()["checkout_id"] == second.json()["checkout_id"] == key
    shopper_a.wait_for_outcome(key)
    orders = [o for o in shopper_a.get("/orders").json() if o["checkout_id"] == key]
    assert len(orders) == 1


def test_empty_cart_is_refused(shopper_a):
    shopper_a.set_cart([])
    r = shopper_a.checkout()
    assert r.status_code == 400 and r.json()["error"] == "EMPTY_CART"


def test_unknown_sku_cannot_enter_the_cart(shopper_a):
    r = shopper_a.put("/cart", {"items": [{"sku": "NOPE-404", "qty": 1}]})
    assert r.status_code == 400 and r.json()["error"] == "UNKNOWN_SKU"


def test_declined_payment_is_rejected_without_stock_change(base_url):
    from conftest import Api, get_tokens, need
    email = need("FS_DECLINE_EMAIL")
    api = Api(base_url, get_tokens(email, need("FS_TEST_PASSWORD"))["access_token"])
    before = stock(api, "BAG-001")
    api.set_cart([{"sku": "BAG-001", "qty": 1}])
    key = str(uuid.uuid4())
    assert api.checkout(key).status_code == 202
    outcome = api.wait_for_outcome(key)
    assert (outcome["status"], outcome["reason"]) == ("REJECTED", "PAYMENT_DECLINED")
    assert stock(api, "BAG-001") >= before


def test_pilot_traffic_split_is_about_90_10(anon):
    n = int(os.environ.get("FS_SPLIT_SAMPLES", "400"))
    seen = collections.Counter(anon.get("/version").json()["version"] for _ in range(n))
    assert set(seen) == {"v1", "v2"}, seen
    share = seen["v2"] / n
    # 10% target; 400 samples gives a 95% interval of roughly 7-13%.
    assert 0.04 <= share <= 0.18, f"v2 share {share:.1%} ({seen})"
