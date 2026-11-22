"""API tests generated from specs/RSA-001-request-help.md."""

import pytest

VALID = {"type": "tow", "location": "Main St & 5th", "phone": "+1 555 010 1234"}


@pytest.mark.ac("RSA-001-AC1")
def test_member_creates_a_received_request(as_user):
    r = as_user("alice").post("/v1/requests", json=VALID)
    assert r.status_code == 201
    body = r.json()
    assert body["id"].startswith("RSA-")
    assert body["status"] == "received"
    assert body["member"] == "alice"


@pytest.mark.ac("RSA-001-AC2")
def test_unknown_help_type_is_rejected(as_user):
    r = as_user("alice").post("/v1/requests", json={**VALID, "type": "boat"})
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"
    assert "type" in [e["field"] for e in r.json()["errors"]]


@pytest.mark.ac("RSA-001-AC3")
def test_short_phone_is_rejected(as_user):
    r = as_user("alice").post("/v1/requests", json={**VALID, "phone": "12345"})
    assert r.status_code == 422
    assert "phone" in [e["field"] for e in r.json()["errors"]]


@pytest.mark.ac("RSA-001-AC4")
def test_dispatcher_cannot_create_requests(as_user):
    r = as_user("dana").post("/v1/requests", json=VALID)
    assert r.status_code == 403
    assert r.json()["code"] == "FORBIDDEN"


@pytest.mark.ac("RSA-001-AC5")
def test_creating_a_request_is_audited(as_user, new_request):
    created = new_request("bob")
    events = as_user("dana").get("/v1/audit", params={"event": "request.created", "target": created["id"]}).json()
    assert len(events) == 1
    assert events[0]["actor"] == "bob"
