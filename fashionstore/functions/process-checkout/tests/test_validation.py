import pytest

from service import InvalidMessage, parse_request

VALID = {
    "schema_version": 1,
    "checkout_id": "3f6c2b1e-8a4d-4c6e-9b7a-1d2e3f4a5b6c",
    "user_sub": "user-1",
    "email": "a@example.com",
    "items": [{"sku": "B", "qty": 1}, {"sku": "A", "qty": 2}, {"sku": "B", "qty": 3}],
    "requested_at": "2026-11-11T11:11:00Z",
}


def test_merges_duplicate_skus_and_sorts_for_lock_order():
    req = parse_request(VALID)
    assert [(i.sku, i.qty) for i in req.items] == [("A", 2), ("B", 4)]


@pytest.mark.parametrize("patch", [
    {"schema_version": 2},
    {"checkout_id": "not-a-uuid"},
    {"checkout_id": "3F6C2B1E-8A4D-4C6E-9B7A-1D2E3F4A5B6C"},
    {"user_sub": ""},
    {"email": "no-at-sign"},
    {"items": []},
    {"items": [{"sku": "A", "qty": 0}]},
    {"items": [{"sku": "A", "qty": 21}]},
    {"items": [{"sku": "A", "qty": True}]},
    {"items": [{"sku": "A", "qty": 15}, {"sku": "A", "qty": 15}]},
    {"items": [{"sku": "", "qty": 1}]},
    {"items": [{"sku": str(i), "qty": 1} for i in range(21)]},
])
def test_rejects_invalid_messages(patch):
    with pytest.raises(InvalidMessage):
        parse_request({**VALID, **patch})


def test_rejects_non_object():
    with pytest.raises(InvalidMessage):
        parse_request(["not", "an", "object"])
