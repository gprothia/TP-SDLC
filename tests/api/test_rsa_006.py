"""API tests generated from specs/RSA-006-rate-my-rescue.md."""

from __future__ import annotations

import json
import uuid

import pytest

STEPS = ("assigned", "en_route", "arrived", "completed")


def _advance_to(
    as_user,
    req_id: str,
    target_status: str,
    *,
    owner: str = "alice",
    assign_driver: bool = True,
    driver_name: str = "Sam",
    driver_truck: str = "Truck 12",
) -> None:
    if target_status == "received":
        return
    if target_status == "cancelled":
        r = as_user(owner).post(f"/v1/requests/{req_id}/cancel")
        assert r.status_code == 200, r.text
        return
    for step in STEPS:
        payload: dict = {"status": step}
        if step == "assigned" and assign_driver:
            payload["driver"] = f"{driver_name} ({driver_truck})"
            payload["driver_name"] = driver_name
            payload["driver_truck"] = driver_truck
        r = as_user("dana").patch(f"/v1/requests/{req_id}", json=payload)
        assert r.status_code == 200, r.text
        if step == target_status:
            break


@pytest.mark.ac("RSA-006-AC1")
def test_member_rates_completed_request(as_user, new_request):
    req = new_request("alice")
    _advance_to(as_user, req["id"], "completed", driver_name="Sam", driver_truck="Truck 12")

    r = as_user("alice").post(
        f"/v1/requests/{req['id']}/rating",
        json={
            "stars": 5,
            "tags": ["on_time", "friendly_driver"],
            "comment": "Arrived on time and changed the flat safely",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["request_id"] == req["id"]
    assert body["stars"] == 5
    assert body["tags"] == ["on_time", "friendly_driver"]
    assert body["comment"] == "Arrived on time and changed the flat safely"
    assert body["moderation_status"] == "pending"
    assert isinstance(body["driver_monthly_average"], int | float)
    assert 1.0 <= body["driver_monthly_average"] <= 5.0
    assert isinstance(body["driver_monthly_count"], int)
    assert body["driver_monthly_count"] >= 1


@pytest.mark.ac("RSA-006-AC2")
@pytest.mark.parametrize("case", ["received", "assigned", "en_route", "arrived", "cancelled", "completed_no_driver"])
def test_cannot_rate_uncompleted_or_driverless_request(as_user, new_request, case):
    req = new_request("alice")
    if case == "completed_no_driver":
        _advance_to(as_user, req["id"], "completed", assign_driver=False)
    else:
        _advance_to(as_user, req["id"], case)

    r = as_user("alice").post(f"/v1/requests/{req['id']}/rating", json={"stars": 5})
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "INVALID_TRANSITION"


@pytest.mark.ac("RSA-006-AC3")
@pytest.mark.parametrize(
    ("payload", "expected_field"),
    [
        ({"stars": 6}, "stars"),
        ({"stars": 0}, "stars"),
        ({"stars": 5, "tags": ["super_fast"]}, "tags"),
        ({"stars": 5, "comment": "x" * 301}, "comment"),
    ],
)
def test_rating_validation_errors(as_user, new_request, payload, expected_field):
    req = new_request("alice")
    _advance_to(as_user, req["id"], "completed")

    r = as_user("alice").post(f"/v1/requests/{req['id']}/rating", json=payload)
    assert r.status_code == 422, r.text
    body = r.json()
    assert body["code"] == "VALIDATION_ERROR"
    fields = [e["field"] for e in body["errors"]]
    assert any(f == expected_field or f.startswith(f"{expected_field}[") for f in fields), fields


@pytest.mark.ac("RSA-006-AC4")
def test_cannot_rate_same_request_twice(as_user, new_request):
    req = new_request("alice")
    _advance_to(as_user, req["id"], "completed")

    first = as_user("alice").post(f"/v1/requests/{req['id']}/rating", json={"stars": 5})
    assert first.status_code == 201, first.text

    second = as_user("alice").post(f"/v1/requests/{req['id']}/rating", json={"stars": 4})
    assert second.status_code == 409, second.text
    assert second.json()["code"] == "ALREADY_RATED"


@pytest.mark.ac("RSA-006-AC5")
def test_member_cannot_rate_another_members_request(as_user, new_request):
    req = new_request("bob")
    _advance_to(as_user, req["id"], "completed", owner="bob")

    r = as_user("alice").post(f"/v1/requests/{req['id']}/rating", json={"stars": 5})
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "REQUEST_NOT_FOUND"


@pytest.mark.ac("RSA-006-AC6")
def test_dispatcher_cannot_submit_member_rating(as_user, new_request):
    req = new_request("alice")
    _advance_to(as_user, req["id"], "completed")

    r = as_user("dana").post(f"/v1/requests/{req['id']}/rating", json={"stars": 5})
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "FORBIDDEN"


@pytest.mark.ac("RSA-006-AC7")
@pytest.mark.needs_test_hooks
def test_rating_writes_audit_event_and_omits_comment_from_logs(api, as_user, new_request):
    req = new_request("alice")
    _advance_to(as_user, req["id"], "completed")

    comment = "Call me at +1 555 010 9988 if needed"
    r = as_user("alice").post(
        f"/v1/requests/{req['id']}/rating",
        json={"stars": 5, "tags": ["on_time"], "comment": comment},
    )
    assert r.status_code == 201, r.text

    events = as_user("dana").get("/v1/audit", params={"event": "rating.created", "target": req["id"]}).json()
    assert len(events) == 1
    assert events[0]["actor"] == "alice"
    assert events[0]["target"] == req["id"]
    assert events[0]["stars"] == 5
    assert events[0]["tags"] == ["on_time"]
    assert events[0]["has_comment"] is True

    audit_blob = json.dumps(events)
    assert "Call me at" not in audit_blob
    assert "010 9988" not in audit_blob

    logs_blob = json.dumps(api.get("/test/logs", params={"limit": 100}).json())
    assert "Call me at" not in logs_blob
    assert "010 9988" not in logs_blob


@pytest.mark.ac("RSA-006-AC8")
def test_leaderboard_requires_auth_and_ranks_drivers_without_pii(api, as_user, new_request):
    unauth = api.get("/v1/leaderboard/drivers")
    assert unauth.status_code == 401
    assert unauth.json()["code"] == "UNAUTHENTICATED"

    uid = uuid.uuid4().hex[:6]
    marcus_first = f"Marcus{uid}"
    devon_first = f"Devon{uid}"

    r1 = new_request("alice")
    _advance_to(as_user, r1["id"], "completed", driver_name=f"{marcus_first} Rivera", driver_truck="Flatbed #418")
    approved_note = f"Approved rescue note {uid}"
    assert (
        as_user("alice")
        .post(
            f"/v1/requests/{r1['id']}/rating",
            json={"stars": 5, "tags": ["on_time", "friendly_driver"], "comment": approved_note},
        )
        .status_code
        == 201
    )
    assert (
        as_user("dana").patch(f"/v1/requests/{r1['id']}/rating", json={"moderation_status": "approved"}).status_code
        == 200
    )

    r2 = new_request("bob")
    _advance_to(
        as_user,
        r2["id"],
        "completed",
        owner="bob",
        driver_name=f"{marcus_first} Rivera",
        driver_truck="Flatbed #418",
    )
    pending_note = f"Pending private note {uid}"
    assert (
        as_user("bob")
        .post(
            f"/v1/requests/{r2['id']}/rating",
            json={"stars": 5, "tags": ["explained_fix"], "comment": pending_note},
        )
        .status_code
        == 201
    )

    r3 = new_request("alice")
    _advance_to(as_user, r3["id"], "completed", driver_name=f"{devon_first} Clark", driver_truck="Unit #507")
    rejected_note = f"Rejected note {uid}"
    assert (
        as_user("alice")
        .post(f"/v1/requests/{r3['id']}/rating", json={"stars": 3, "tags": ["on_time"], "comment": rejected_note})
        .status_code
        == 201
    )
    assert (
        as_user("dana").patch(f"/v1/requests/{r3['id']}/rating", json={"moderation_status": "rejected"}).status_code
        == 200
    )

    for role_user in ("alice", "dana"):
        resp = as_user(role_user).get("/v1/leaderboard/drivers")
        assert resp.status_code == 200, resp.text
        drivers = resp.json()["drivers"]

        # Verify ordering: average_stars desc, rating_count desc, driver_display_name asc
        keys = [(-d["average_stars"], -d["rating_count"], d["driver_display_name"].lower()) for d in drivers]
        assert keys == sorted(keys)
        assert [d["rank"] for d in drivers] == list(range(1, len(drivers) + 1))

        by_name = {d["driver_display_name"]: d for d in drivers}
        assert marcus_first in by_name
        assert devon_first in by_name

        marcus = by_name[marcus_first]
        devon = by_name[devon_first]
        assert marcus["rank"] < devon["rank"]
        assert "Rivera" not in marcus["driver_display_name"]
        assert "driver_photo" not in marcus
        assert marcus["driver_truck"] == "Flatbed #418"
        assert marcus["average_stars"] == 5.0
        assert marcus["rating_count"] == 2
        assert marcus["tag_counts"] == {"on_time": 1, "friendly_driver": 1, "explained_fix": 1}
        assert approved_note in marcus["approved_comments"]
        assert pending_note not in marcus["approved_comments"]
        assert all("alice" not in c.lower() and "bob" not in c.lower() for c in marcus["approved_comments"])

        assert "Clark" not in devon["driver_display_name"]
        assert rejected_note not in devon["approved_comments"]


@pytest.mark.ac("RSA-006-AC9")
def test_dispatcher_moderates_rating_comment_and_audits(as_user, new_request):
    uid = uuid.uuid4().hex[:6]
    elena_first = f"Elena{uid}"

    r_ok = new_request("alice")
    _advance_to(as_user, r_ok["id"], "completed", driver_name=f"{elena_first} Brooks", driver_truck="Service Van #204")
    ok_comment = f"Checked the alternator too {uid}"
    assert (
        as_user("alice").post(f"/v1/requests/{r_ok['id']}/rating", json={"stars": 5, "comment": ok_comment}).status_code
        == 201
    )

    r_rej = new_request("bob")
    _advance_to(
        as_user,
        r_rej["id"],
        "completed",
        owner="bob",
        driver_name=f"{elena_first} Brooks",
        driver_truck="Service Van #204",
    )
    rej_comment = f"Should stay hidden {uid}"
    assert (
        as_user("bob").post(f"/v1/requests/{r_rej['id']}/rating", json={"stars": 4, "comment": rej_comment}).status_code
        == 201
    )

    # Before moderation neither comment is visible
    before = {d["driver_display_name"]: d for d in as_user("alice").get("/v1/leaderboard/drivers").json()["drivers"]}
    assert ok_comment not in before[elena_first]["approved_comments"]
    assert rej_comment not in before[elena_first]["approved_comments"]

    # Approve first comment
    mod_ok = as_user("dana").patch(f"/v1/requests/{r_ok['id']}/rating", json={"moderation_status": "approved"})
    assert mod_ok.status_code == 200, mod_ok.text
    assert mod_ok.json()["moderation_status"] == "approved"

    # Reject second comment
    mod_rej = as_user("dana").patch(f"/v1/requests/{r_rej['id']}/rating", json={"moderation_status": "rejected"})
    assert mod_rej.status_code == 200, mod_rej.text
    assert mod_rej.json()["moderation_status"] == "rejected"

    # Verify audit events
    ev_ok = as_user("dana").get("/v1/audit", params={"event": "rating.moderated", "target": r_ok["id"]}).json()
    assert len(ev_ok) == 1
    assert ev_ok[0]["actor"] == "dana"
    assert ev_ok[0]["moderation_status"] == "approved"

    ev_rej = as_user("dana").get("/v1/audit", params={"event": "rating.moderated", "target": r_rej["id"]}).json()
    assert len(ev_rej) == 1
    assert ev_rej[0]["actor"] == "dana"
    assert ev_rej[0]["moderation_status"] == "rejected"

    # Verify leaderboard reflects moderation decisions
    after = {d["driver_display_name"]: d for d in as_user("alice").get("/v1/leaderboard/drivers").json()["drivers"]}
    assert ok_comment in after[elena_first]["approved_comments"]
    assert rej_comment not in after[elena_first]["approved_comments"]


@pytest.mark.ac("RSA-006-AC10")
def test_member_cannot_moderate_rating_comment(as_user, new_request):
    req = new_request("alice")
    _advance_to(as_user, req["id"], "completed")
    assert (
        as_user("alice")
        .post(f"/v1/requests/{req['id']}/rating", json={"stars": 5, "comment": "Helpful driver"})
        .status_code
        == 201
    )

    r = as_user("alice").patch(f"/v1/requests/{req['id']}/rating", json={"moderation_status": "approved"})
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "FORBIDDEN"
