"""API tests for specs/RSA-006-rate-my-rescue.md."""

import pytest


def _complete_request(as_user, new_request, member: str = "alice", driver_name: str = "Marcus Rivera") -> dict:
    req = new_request(member)
    dana = as_user("dana")
    for idx, status in enumerate(["assigned", "en_route", "arrived", "completed"]):
        payload = {"status": status}
        if idx == 0:
            payload["driver_name"] = driver_name
            payload["driver_truck"] = "Flatbed #418"
        r = dana.patch(f"/v1/requests/{req['id']}", json=payload)
        assert r.status_code == 200, r.text
    return req


@pytest.mark.ac("RSA-006-AC1")
def test_submit_rating_on_completed_rescue(as_user, new_request):
    req = _complete_request(as_user, new_request, member="alice", driver_name="Marcus Rivera")
    r = as_user("alice").post(
        f"/v1/requests/{req['id']}/rating",
        json={
            "stars": 5,
            "tags": ["On time", "Friendly driver"],
            "comment": "Swapped my flat in 12 minutes.",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["rating"]["stars"] == 5
    assert body["rating"]["tags"] == ["On time", "Friendly driver"]
    assert body["rating"]["comment"] == "Swapped my flat in 12 minutes."
    assert body["rating"]["submitted_at"]
    assert isinstance(body["driver_monthly_avg"], (int, float))


@pytest.mark.ac("RSA-006-AC2")
def test_reject_rating_for_non_completed_rescue(as_user, new_request):
    req = new_request("alice")
    r = as_user("alice").post(f"/v1/requests/{req['id']}/rating", json={"stars": 5})
    assert r.status_code == 409
    assert r.json()["code"] == "INVALID_STATUS"


@pytest.mark.ac("RSA-006-AC3")
def test_reject_duplicate_rating(as_user, new_request):
    req = _complete_request(as_user, new_request, member="alice")
    first = as_user("alice").post(f"/v1/requests/{req['id']}/rating", json={"stars": 5})
    assert first.status_code == 201

    second = as_user("alice").post(f"/v1/requests/{req['id']}/rating", json={"stars": 4})
    assert second.status_code == 409
    assert second.json()["code"] == "ALREADY_RATED"


@pytest.mark.ac("RSA-006-AC4")
@pytest.mark.parametrize(
    ("payload", "expected_field"),
    [
        ({"stars": 6}, "stars"),
        ({"stars": 0}, "stars"),
        ({"stars": 5, "tags": ["Super fast"]}, "tags"),
        ({"stars": 5, "comment": "x" * 301}, "comment"),
    ],
)
def test_rating_validation_errors(as_user, new_request, payload, expected_field):
    req = _complete_request(as_user, new_request, member="alice")
    r = as_user("alice").post(f"/v1/requests/{req['id']}/rating", json=payload)
    assert r.status_code == 422, r.text
    body = r.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert any(expected_field in err["field"] for err in body["errors"])


@pytest.mark.ac("RSA-006-AC5")
def test_rating_auth_and_isolation(api, as_user, new_request):
    bobs_req = _complete_request(as_user, new_request, member="bob")

    unauth = api.post(f"/v1/requests/{bobs_req['id']}/rating", json={"stars": 5})
    assert unauth.status_code == 401
    assert unauth.json()["code"] == "UNAUTHENTICATED"

    other_member = as_user("alice").post(f"/v1/requests/{bobs_req['id']}/rating", json={"stars": 5})
    assert other_member.status_code == 404
    assert other_member.json()["code"] == "REQUEST_NOT_FOUND"

    dispatcher = as_user("dana").post(f"/v1/requests/{bobs_req['id']}/rating", json={"stars": 5})
    assert dispatcher.status_code == 403
    assert dispatcher.json()["code"] == "FORBIDDEN"


@pytest.mark.ac("RSA-006-AC6")
def test_rating_audit_event(as_user, new_request):
    req = _complete_request(as_user, new_request, member="alice", driver_name="Elena Brooks")
    r = as_user("alice").post(
        f"/v1/requests/{req['id']}/rating",
        json={"stars": 4, "tags": ["On time"]},
    )
    assert r.status_code == 201

    audit_resp = as_user("dana").get("/v1/audit", params={"event": "rating.submitted", "target": req["id"]})
    assert audit_resp.status_code == 200
    events = audit_resp.json()
    assert len(events) >= 1
    ev = events[0]
    assert ev["actor"] == "alice"
    assert ev["target"] == req["id"]
    assert ev["stars"] == 4
    assert ev["driver_name"] == "Elena Brooks"


@pytest.mark.ac("RSA-006-AC7")
def test_leaderboard_endpoint_and_auth(api, as_user):
    unauth = api.get("/v1/drivers/leaderboard")
    assert unauth.status_code == 401
    assert unauth.json()["code"] == "UNAUTHENTICATED"

    disp = as_user("dana").get("/v1/drivers/leaderboard")
    assert disp.status_code == 403
    assert disp.json()["code"] == "FORBIDDEN"

    r = as_user("alice").get("/v1/drivers/leaderboard")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["month"]
    assert isinstance(body["fleet_avg_stars"], (int, float))
    assert body["total_ratings"] >= 1
    drivers = body["drivers"]
    assert len(drivers) >= 1
    avgs = [d["avg_stars"] for d in drivers]
    assert avgs == sorted(avgs, reverse=True)
    for d in drivers:
        assert d["rating_count"] >= 1
        assert d["driver_name"]
        assert "truck" in d
        assert "photo_url" in d
        assert "tag_counts" in d
        assert "latest_quote" in d

    filtered = as_user("alice").get("/v1/drivers/leaderboard", params={"tag": "On time"})
    assert filtered.status_code == 200
    for d in filtered.json()["drivers"]:
        assert d["tag_counts"].get("On time", 0) > 0
