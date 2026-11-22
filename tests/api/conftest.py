import os

import httpx
import pytest

BASE = os.environ.get("API_BASE_URL", "http://localhost:8080")
# UAT on Cloud Run: the API is private, so CI passes a Google identity token. It travels in
# X-Serverless-Authorization, leaving Authorization for the app's own sign-in token.
IAM_TOKEN = os.environ.get("API_IAM_TOKEN")
PLATFORM = {"X-Serverless-Authorization": f"Bearer {IAM_TOKEN}"} if IAM_TOKEN else {}


def pytest_configure(config):
    config.addinivalue_line("markers", "ac(id): acceptance criterion this test verifies")
    config.addinivalue_line(
        "markers", "needs_test_hooks: uses /test/... endpoints; skipped in UAT, where test hooks are off"
    )


def pytest_collection_modifyitems(items):
    # Put the criterion ID into the JUnit report so failures map straight back to the spec.
    for item in items:
        for mark in item.iter_markers("ac"):
            item.user_properties.append(("acceptance_criterion", mark.args[0]))


@pytest.fixture(scope="session")
def api():
    """A client with no user signed in."""
    with httpx.Client(base_url=BASE, timeout=15, headers=PLATFORM) as client:
        yield client


@pytest.fixture(scope="session")
def token(api):
    """token('alice') -> a signed-in user's bearer token (demo sign-in, standards/aaa.md AAA-3)."""
    cache: dict[str, str] = {}

    def get(user: str) -> str:
        if user not in cache:
            r = api.post("/v1/auth/demo-login", json={"user": user})
            assert r.status_code == 200, r.text
            cache[user] = r.json()["token"]
        return cache[user]

    return get


@pytest.fixture(scope="session")
def as_user(token):
    """as_user('alice') -> a client signed in as that user."""
    clients: list[httpx.Client] = []

    def make(user: str) -> httpx.Client:
        c = httpx.Client(base_url=BASE, timeout=15, headers={**PLATFORM, "Authorization": f"Bearer {token(user)}"})
        clients.append(c)
        return c

    yield make
    for c in clients:
        c.close()


@pytest.fixture
def new_request(as_user):
    """Create a request as a member and return it."""

    def make(user: str = "alice", **overrides) -> dict:
        body = {"type": "tow", "location": "Main St & 5th", "phone": "+1 555 010 1234", **overrides}
        r = as_user(user).post("/v1/requests", json=body)
        assert r.status_code == 201, r.text
        return r.json()

    return make
