"""API tests generated from specs/RSA-006-rate-my-rescue.md."""

import pytest


def _create_completed_request(as_user, new_request, driver_name="Sam"):
    req = new_request("alice")
    as_user("dana").patch(
        f"/v1/requests/{req['id']}",
        json={
            "status": "assigned",
            "eta_minutes": 15,
            "driver": driver_name,
            "driver_name": driver_name,
            "driver_truck": "Truck #T-204",
        },
    )
    for status in ("en_route", "arrived", "completed"):
        r = as_user("dana").patch(f"/v1/requests/{req['id']}", json={"status": status})
        assert r.status_code == 200
    return req


@pytest.mark.ac("RSA-006-AC1")
def test_rate_completed_rescue(as_user, new_request):
    req = _create_completed_request(as_user, new_request, driver_name="Sam")
    r = as_user("alice").post(
        f"/v1/requests/{req['id']}/rating",
        json={
            "stars": 5,
            "tags": ["On time", "Friendly driver"],
            "comment": "Quick jump-start!",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["request_id"] == req["id"]
    assert body["driver_name"] == "Sam"
    assert body["stars"] == 5
    assert body["tags"] == ["On time", "Friendly driver"]
    assert body["comment"] == "Quick jump-start!"
    assert "created_at" in body


@pytest.mark.ac("RSA-006-AC2")
def test_cannot_rate_non_completed_rescue(as_user, new_request):
    req = new_request("alice")
    as_user("dana").patch(
        f"/v1/requests/{req['id']}",
        json={"status": "assigned", "eta_minutes": 14, "driver_name": "Sam"},
    )
    as_user("dana").patch(f"/v1/requests/{req['id']}", json={"status": "en_route", "eta_minutes": 10})

    r = as_user("alice").post(f"/v1/requests/{req['id']}/rating", json={"stars": 5})
    assert r.status_code == 409
    assert r.json()["code"] == "INVALID_TRANSITION"


@pytest.mark.ac("RSA-006-AC3")
def test_cannot_rate_already_rated_rescue(as_user, new_request):
    req = _create_completed_request(as_user, new_request)
    first = as_user("alice").post(f"/v1/requests/{req['id']}/rating", json={"stars": 5})
    assert first.status_code == 201

    second = as_user("alice").post(f"/v1/requests/{req['id']}/rating", json={"stars": 4})
    assert second.status_code == 409
    assert second.json()["code"] == "ALREADY_RATED"


@pytest.mark.ac("RSA-006-AC4")
def test_rating_validation_errors(as_user, new_request):
    req = _create_completed_request(as_user, new_request)

    bad_stars = as_user("alice").post(f"/v1/requests/{req['id']}/rating", json={"stars": 6})
    assert bad_stars.status_code == 422
    assert bad_stars.json()["code"] == "VALIDATION_ERROR"
    assert any(err["field"] == "stars" for err in bad_stars.json()["errors"])

    bad_tag = as_user("alice").post(
        f"/v1/requests/{req['id']}/rating",
        json={"stars": 5, "tags": ["Unknown tag"]},
    )
    assert bad_tag.status_code == 422
    assert bad_tag.json()["code"] == "VALIDATION_ERROR"
    assert any(err["field"] == "tags" for err in bad_tag.json()["errors"])

    bad_comment = as_user("alice").post(
        f"/v1/requests/{req['id']}/rating",
        json={"stars": 5, "comment": "x" * 301},
    )
    assert bad_comment.status_code == 422
    assert bad_comment.json()["code"] == "VALIDATION_ERROR"
    assert any(err["field"] == "comment" for err in bad_comment.json()["errors"])


@pytest.mark.ac("RSA-006-AC5")
def test_member_cannot_rate_another_members_rescue(as_user):
    r = as_user("alice").post("/v1/requests/RSA-1001/rating", json={"stars": 5})
    assert r.status_code == 404
    assert r.json()["code"] == "REQUEST_NOT_FOUND"


@pytest.mark.ac("RSA-006-AC6")
def test_dispatcher_cannot_rate_rescue(as_user, new_request):
    req = _create_completed_request(as_user, new_request)
    r = as_user("dana").post(f"/v1/requests/{req['id']}/rating", json={"stars": 5})
    assert r.status_code == 403
    assert r.json()["code"] == "FORBIDDEN"


@pytest.mark.ac("RSA-006-AC7")
def test_unauthenticated_rating_and_leaderboard_rejected(api, new_request):
    req = new_request("alice")
    r_rate = api.post(f"/v1/requests/{req['id']}/rating", json={"stars": 5})
    assert r_rate.status_code == 401
    assert r_rate.json()["code"] == "UNAUTHENTICATED"

    r_board = api.get("/v1/drivers/leaderboard")
    assert r_board.status_code == 401
    assert r_board.json()["code"] == "UNAUTHENTICATED"


@pytest.mark.ac("RSA-006-AC8")
@pytest.mark.needs_test_hooks
def test_rating_writes_audit_event_and_omits_comment_from_logs(api, as_user, new_request):
    req = _create_completed_request(as_user, new_request)
    private_comment = "Private member feedback phrase 98765"
    r = as_user("alice").post(
        f"/v1/requests/{req['id']}/rating",
        json={"stars": 5, "tags": ["On time"], "comment": private_comment},
    )
    assert r.status_code == 201

    events = as_user("dana").get("/v1/audit", params={"event": "rating.created", "target": req["id"]}).json()
    assert len(events) == 1
    assert events[0]["actor"] == "alice"
    assert events[0]["target"] == req["id"]
    assert events[0]["stars"] == 5
    assert events[0]["tags"] == ["On time"]

    logs = api.get("/test/logs", params={"limit": 30}).json()
    assert all(private_comment not in str(entry) for entry in logs)


@pytest.mark.ac("RSA-006-AC9")
def test_leaderboard_returns_qualified_drivers_without_comments(as_user, new_request):
    req = _create_completed_request(as_user, new_request, driver_name="Sam")
    as_user("alice").post(
        f"/v1/requests/{req['id']}/rating",
        json={"stars": 5, "comment": "Private note that must not appear on leaderboard"},
    )

    r = as_user("alice").get("/v1/drivers/leaderboard")
    assert r.status_code == 200
    drivers = r.json()["drivers"]
    assert len(drivers) >= 1
    for driver in drivers:
        assert driver["rating_count"] >= 5
        for key in ("driver_name", "photo_url", "truck_unit", "rescue_count", "rating_count", "average_stars"):
            assert key in driver
        assert "comment" not in driver
        assert "comments" not in driver

    sorted_drivers = sorted(
        drivers,
        key=lambda d: (-d["average_stars"], -d["rescue_count"]),
    )
    assert drivers == sorted_drivers
