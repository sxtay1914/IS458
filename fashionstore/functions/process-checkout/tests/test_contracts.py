"""Published events must match contracts/events/checkout-status.schema.json."""
import json
import uuid

import jsonschema
import pytest

from fashionstore_common.testing import CONTRACTS
from service import Outcome


def schema(name):
    return json.loads((CONTRACTS / "events" / name).read_text())


@pytest.mark.parametrize("example,schema_name", [
    ("checkout-request.json", "checkout-request.schema.json"),
    ("checkout-confirmed.json", "checkout-status.schema.json"),
    ("checkout-rejected.json", "checkout-status.schema.json"),
])
def test_examples_match_schemas(example, schema_name):
    jsonschema.validate(json.loads((CONTRACTS / "examples" / example).read_text()), schema(schema_name))


@pytest.mark.parametrize("status,reason", [("CONFIRMED", None), ("REJECTED", "OUT_OF_STOCK")])
def test_outcome_event_matches_status_schema(status, reason):
    event = Outcome(str(uuid.uuid4()), status, reason, 7, "user-1", "a@example.com", 5990).to_event()
    jsonschema.validate(event, schema("checkout-status.schema.json"))


def test_rejected_without_reason_is_invalid():
    event = Outcome(str(uuid.uuid4()), "REJECTED", None, 7, "user-1", "a@example.com", 5990).to_event()
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(event, schema("checkout-status.schema.json"))


def test_example_request_is_accepted_by_parser():
    from service import parse_request
    req = parse_request(json.loads((CONTRACTS / "examples" / "checkout-request.json").read_text()))
    assert len(req.items) == 2
