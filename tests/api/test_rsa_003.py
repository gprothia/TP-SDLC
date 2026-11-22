"""API tests generated from specs/RSA-003-dispatcher-update.md."""

import pytest


@pytest.mark.ac("RSA-003-AC1")
def test_dispatcher_assigns_a_truck(as_user, new_request):
    req = new_request()
    r = as_user("dana").patch(
        f"/v1/requests/{req['id']}", json={"status": "assigned", "eta_minutes": 20, "driver": "Sam (Truck 12)"}
    )
    assert r.status_code == 200
    body = r.json()
    assert (body["status"], body["eta_minutes"], body["driver"]) == ("assigned", 20, "Sam (Truck 12)")
    assert body["history"][-1]["status"] == "assigned"


@pytest.mark.ac("RSA-003-AC2")
def test_skipping_a_status_is_rejected(as_user, new_request):
    req = new_request()
    r = as_user("dana").patch(f"/v1/requests/{req['id']}", json={"status": "en_route"})
    assert r.status_code == 409
    assert r.json()["code"] == "INVALID_TRANSITION"


@pytest.mark.ac("RSA-003-AC3")
def test_member_cannot_update_requests(as_user, new_request):
    req = new_request("alice")
    r = as_user("alice").patch(f"/v1/requests/{req['id']}", json={"status": "assigned"})
    assert r.status_code == 403
    assert r.json()["code"] == "FORBIDDEN"


@pytest.mark.ac("RSA-003-AC4")
def test_updates_are_audited(as_user, new_request):
    req = new_request()
    as_user("dana").patch(f"/v1/requests/{req['id']}", json={"status": "assigned", "eta_minutes": 15})
    events = as_user("dana").get("/v1/audit", params={"event": "request.updated", "target": req["id"]}).json()
    assert len(events) == 1
    assert events[0]["actor"] == "dana"
    assert events[0]["changes"] == {"status": "assigned", "eta_minutes": 15}
