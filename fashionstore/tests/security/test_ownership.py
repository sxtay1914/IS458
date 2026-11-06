"""A shopper can never see or reuse another shopper's checkout or order."""
import uuid


def test_other_shoppers_checkout_and_order_are_invisible(shopper_a, shopper_b):
    shopper_a.set_cart([{"sku": "TOP-001-S", "qty": 1}])
    key = str(uuid.uuid4())
    assert shopper_a.checkout(key).status_code == 202
    outcome = shopper_a.wait_for_outcome(key)
    order_id = outcome["order_id"]
    assert order_id

    # Looks like it does not exist (404), not "forbidden" (403), so ids can't be probed.
    assert shopper_b.get(f"/checkouts/{key}").status_code == 404
    assert shopper_b.get(f"/orders/{order_id}").status_code == 404
    assert order_id not in [o["order_id"] for o in shopper_b.get("/orders").json()]
    assert shopper_a.get(f"/orders/{order_id}").status_code == 200


def test_idempotency_key_of_another_shopper_is_refused(shopper_a, shopper_b):
    shopper_a.set_cart([{"sku": "TOP-001-S", "qty": 1}])
    key = str(uuid.uuid4())
    assert shopper_a.checkout(key).status_code == 202

    shopper_b.set_cart([{"sku": "BTM-001-M", "qty": 1}])
    r = shopper_b.checkout(key)
    assert r.status_code == 409
    assert r.json()["error"] == "IDEMPOTENCY_KEY_REUSED"
    assert shopper_b.get("/cart").json()["items"], "B's cart must be untouched"
    shopper_b.set_cart([])
