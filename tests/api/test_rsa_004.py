"""API tests generated from specs/RSA-004-track-my-rescue-live.md."""

import pytest


@pytest.mark.ac("RSA-004-AC4")
def test_get_request_returns_driver_details(as_user, new_request):
    req = new_request("alice")
    patch = as_user("dana").patch(
        f"/v1/requests/{req['id']}",
        json={
            "status": "assigned",
            "eta_minutes": 14,
            "driver": "Marcus Rivera (Flatbed #418)",
            "driver_name": "Marcus Rivera",
            "driver_truck": "Flatbed #418 • White Ford F-550",
            "driver_rating": 4.9,
            "driver_phone": "(555) 014-8392",
        },
    )
    assert patch.status_code == 200

    r = as_user("alice").get(f"/v1/requests/{req['id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["driver_name"] == "Marcus Rivera"
    assert body["driver_truck"] == "Flatbed #418 • White Ford F-550"
    assert body["driver_rating"] == 4.9
    assert body["driver_phone"] == "(555) 014-8392"


@pytest.mark.ac("RSA-004-AC6")
def test_unauthenticated_get_request_rejected(api, new_request):
    req = new_request("alice")
    r = api.get(f"/v1/requests/{req['id']}")
    assert r.status_code == 401
    assert r.json()["code"] == "UNAUTHENTICATED"


@pytest.mark.ac("RSA-004-AC7")
def test_member_cancels_active_request(as_user, new_request):
    req = new_request("alice")
    as_user("dana").patch(f"/v1/requests/{req['id']}", json={"status": "assigned", "eta_minutes": 18})
    as_user("dana").patch(f"/v1/requests/{req['id']}", json={"status": "en_route", "eta_minutes": 14})

    r = as_user("alice").post(f"/v1/requests/{req['id']}/cancel")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "cancelled"
    assert body["history"][-1]["status"] == "cancelled"


@pytest.mark.ac("RSA-004-AC8")
def test_cannot_cancel_arrived_or_cancelled_request(as_user, new_request):
    req = new_request("alice")
    for nxt in ("assigned", "en_route", "arrived"):
        as_user("dana").patch(f"/v1/requests/{req['id']}", json={"status": nxt})

    r = as_user("alice").post(f"/v1/requests/{req['id']}/cancel")
    assert r.status_code == 409
    assert r.json()["code"] == "INVALID_TRANSITION"


@pytest.mark.ac("RSA-004-AC9")
def test_member_cannot_cancel_another_members_request(as_user):
    r = as_user("alice").post("/v1/requests/RSA-1001/cancel")
    assert r.status_code == 404
    assert r.json()["code"] == "REQUEST_NOT_FOUND"


@pytest.mark.ac("RSA-004-AC10")
def test_dispatcher_cannot_cancel_via_member_endpoint(as_user, new_request):
    req = new_request("alice")
    r = as_user("dana").post(f"/v1/requests/{req['id']}/cancel")
    assert r.status_code == 403
    assert r.json()["code"] == "FORBIDDEN"


@pytest.mark.ac("RSA-004-AC11")
@pytest.mark.needs_test_hooks
def test_cancel_writes_audit_event_and_masks_driver_phone(api, as_user, new_request):
    req = new_request("alice")
    as_user("dana").patch(
        f"/v1/requests/{req['id']}",
        json={
            "status": "assigned",
            "eta_minutes": 14,
            "driver_name": "Marcus Rivera",
            "driver_phone": "(555) 014-8392",
        },
    )
    r = as_user("alice").post(f"/v1/requests/{req['id']}/cancel")
    assert r.status_code == 200

    events = as_user("dana").get("/v1/audit", params={"event": "request.cancelled", "target": req["id"]}).json()
    assert len(events) == 1
    assert events[0]["actor"] == "alice"
    assert events[0]["target"] == req["id"]

    logs = api.get("/test/logs", params={"limit": 30}).json()
    assert all("014-8392" not in str(entry) for entry in logs)
