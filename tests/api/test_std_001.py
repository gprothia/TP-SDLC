"""API tests generated from specs/STD-001-enterprise-baseline.md (standards AAA, API, LOG, SEC-8)."""

import json
import uuid

import pytest

PROTECTED = [
    ("GET", "/v1/me"),
    ("GET", "/v1/audit"),
    ("GET", "/v1/requests"),
    ("POST", "/v1/requests"),
    ("GET", "/v1/requests/RSA-1001"),
    ("PATCH", "/v1/requests/RSA-1001"),
]


@pytest.mark.ac("STD-001-AC1")
@pytest.mark.parametrize(("method", "path"), PROTECTED)
def test_every_v1_endpoint_requires_sign_in(api, method, path):
    # Only POST/PATCH carry a body: Cloud Run's front end rejects a GET with a body (400).
    body = {} if method in ("POST", "PATCH") else None
    r = api.request(method, path, json=body)
    assert r.status_code == 401
    assert r.json()["code"] == "UNAUTHENTICATED"


@pytest.mark.ac("STD-001-AC2")
def test_tampered_token_is_rejected(api, token):
    payload, sig = token("alice").split(".")
    forged = payload + "." + ("A" if sig[0] != "A" else "B") + sig[1:]
    r = api.get("/v1/requests", headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401
    assert r.json()["code"] == "UNAUTHENTICATED"


@pytest.mark.ac("STD-001-AC3")
def test_request_id_is_kept_or_created(as_user):
    alice = as_user("alice")
    assert alice.get("/v1/me", headers={"X-Request-ID": "std-check-123"}).headers["X-Request-ID"] == "std-check-123"
    assert alice.get("/v1/me").headers["X-Request-ID"]


@pytest.mark.ac("STD-001-AC4")
@pytest.mark.parametrize("path", ["/v1/requests", "/v1/no-such-thing"])
def test_errors_have_code_message_and_request_id(api, path):
    r = api.get(path)
    assert r.status_code in (401, 404)
    body = r.json()
    assert body["code"] and body["message"]
    assert body["request_id"] == r.headers["X-Request-ID"]


@pytest.mark.ac("STD-001-AC5")
@pytest.mark.needs_test_hooks
def test_each_request_writes_a_structured_log_line(api, as_user):
    rid = f"log-check-{uuid.uuid4().hex[:8]}"
    as_user("alice").post(
        "/v1/requests",
        json={"type": "fuel", "location": "Route 9", "phone": "+1 555 010 5566"},
        headers={"X-Request-ID": rid},
    )
    lines = [line for line in api.get("/test/logs", params={"limit": 200}).json() if line["request_id"] == rid]
    http = [line for line in lines if line["event"] == "http.request"]
    assert len(http) == 1
    for field in ("ts", "method", "path", "status", "duration_ms", "user", "role"):
        assert field in http[0]
    assert (http[0]["method"], http[0]["path"], http[0]["status"]) == ("POST", "/v1/requests", 201)
    assert (http[0]["user"], http[0]["role"]) == ("alice", "member")


@pytest.mark.ac("STD-001-AC6")
@pytest.mark.needs_test_hooks
def test_phone_numbers_never_logged_in_clear(api, new_request):
    new_request(phone="+1 555 010 4477", location="Call +1 555 010 4477 at the gas station")
    blob = json.dumps(api.get("/test/logs", params={"limit": 200}).json())
    assert "010 4477" not in blob
    assert "0104477" not in blob


@pytest.mark.ac("STD-001-AC7")
def test_sign_in_is_audited(api, as_user):
    api.post("/v1/auth/demo-login", json={"user": "alice"})
    events = as_user("dana").get("/v1/audit", params={"event": "auth.signed_in", "target": "alice"}).json()
    assert events and events[0]["actor"] == "alice"


@pytest.mark.ac("STD-001-AC11")
@pytest.mark.parametrize("signed_in", [False, True])
def test_api_responses_are_not_sniffed_or_cached(api, as_user, signed_in):
    r = as_user("alice").get("/v1/me") if signed_in else api.get("/v1/me")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["Cache-Control"] == "no-store"
