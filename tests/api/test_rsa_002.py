"""API tests generated from specs/RSA-002-view-requests.md."""

import pytest


@pytest.mark.ac("RSA-002-AC1")
def test_member_sees_only_own_requests(as_user, new_request):
    mine = new_request("alice")
    ids = [r["id"] for r in as_user("alice").get("/v1/requests").json()]
    assert mine["id"] in ids
    assert "RSA-1001" not in ids


@pytest.mark.ac("RSA-002-AC2")
def test_dispatcher_sees_all_requests(as_user, new_request):
    alices = new_request("alice")
    rows = as_user("dana").get("/v1/requests").json()
    ids = [r["id"] for r in rows]
    assert "RSA-1001" in ids
    assert alices["id"] in ids
    assert {"alice", "bob"} <= {r["member"] for r in rows}


@pytest.mark.ac("RSA-002-AC3")
def test_member_cannot_see_someone_elses_request(as_user):
    r = as_user("alice").get("/v1/requests/RSA-1001")
    assert r.status_code == 404
    assert r.json()["code"] == "REQUEST_NOT_FOUND"
