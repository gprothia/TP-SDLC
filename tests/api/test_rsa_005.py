"""API tests for specs/RSA-005-verified-driver.md."""

import pytest


@pytest.mark.ac("RSA-005-AC1")
def test_verified_driver_is_flagged(as_user):
    r = as_user("bob").get("/v1/requests/RSA-1001")
    assert r.status_code == 200
    assert r.json()["driver_verified"] is True


@pytest.mark.ac("RSA-005-AC2")
def test_unknown_driver_is_not_verified(as_user, new_request):
    req = new_request("alice")
    patch = as_user("dana").patch(
        f"/v1/requests/{req['id']}", json={"status": "assigned", "driver_name": "Marcus Rivera"}
    )
    assert patch.status_code == 200
    r = as_user("alice").get(f"/v1/requests/{req['id']}")
    assert r.status_code == 200
    assert r.json()["driver_verified"] is False


@pytest.mark.ac("RSA-005-AC3")
def test_no_driver_means_no_verification(as_user, new_request):
    req = new_request("alice")
    r = as_user("alice").get(f"/v1/requests/{req['id']}")
    assert r.status_code == 200
    assert r.json()["driver_verified"] is None
