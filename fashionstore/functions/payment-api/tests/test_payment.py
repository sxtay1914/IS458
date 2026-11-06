import uuid

import pytest

import handler
from handler import BadRequest, decide

CID = "3f6c2b1e-8a4d-4c6e-9b7a-1d2e3f4a5b6c"


def test_same_input_same_answer():
    a = decide(CID, 5990, "a@example.com", 500000, 30)
    b = decide(CID, 5990, "a@example.com", 500000, 30)
    assert a == b and a["payment_ref"].startswith("pay_")


def test_approves_by_default():
    assert decide(CID, 5990, "a@example.com", 500000, 0) == {
        "approved": True, "payment_ref": decide(CID, 1, "a@example.com", 500000, 0)["payment_ref"], "reason": None}


def test_limit_exceeded():
    assert decide(CID, 500001, "a@example.com", 500000, 0)["reason"] == "LIMIT_EXCEEDED"


def test_decline_email_tag():
    r = decide(CID, 100, "Shopper+Decline@example.com", 500000, 0)
    assert r == {**r, "approved": False, "reason": "CARD_DECLINED"}


def test_decline_percent_is_roughly_honoured():
    ids = [str(uuid.UUID(int=i)) for i in range(2000)]
    declined = sum(not decide(i, 100, "a@example.com", 500000, 25)["approved"] for i in ids)
    assert 400 < declined < 600
    assert all(decide(i, 100, "a@example.com", 500000, 0)["approved"] for i in ids[:200])
    assert not any(decide(i, 100, "a@example.com", 500000, 100)["approved"] for i in ids[:200])


@pytest.mark.parametrize("cid,amount,email", [
    ("nope", 1, "a@example.com"), (CID, -1, "a@example.com"), (CID, 1.5, "a@example.com"),
    (CID, True, "a@example.com"), (CID, 1, "bad"), (None, 1, "a@example.com"),
])
def test_bad_requests(cid, amount, email):
    with pytest.raises(BadRequest):
        decide(cid, amount, email, 500000, 0)


def test_handler_reads_env(monkeypatch):
    monkeypatch.setenv("MAX_AMOUNT_CENTS", "100")
    out = handler.lambda_handler({"checkout_id": CID, "amount_cents": 101, "email": "a@example.com"}, None)
    assert out["approved"] is False and out["reason"] == "LIMIT_EXCEEDED"
