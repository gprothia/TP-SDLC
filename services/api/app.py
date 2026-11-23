"""Roadside Assistance API (demo for AAA).

Features (see specs/):
  STD-001  Enterprise baseline: AAA, logging, API standards
  RSA-001  Request roadside help
  RSA-002  View requests (members: their own; dispatchers: all)
  RSA-003  Dispatcher updates a request
  RSA-004  Live track my rescue and member cancellation
  RSA-005  Verified driver badge (partner Driver Directory)
  RSA-006  Rate my rescue and signed-in monthly top drivers leaderboard

Standards applied (see standards/):
  aaa.md      Bearer token on every /v1 endpoint; roles; deny by default; audit events
  api.md      /v1 paths; error body {"code", "message", "request_id"}; X-Request-ID
  logging.md  one JSON log line per request; request_id; phone numbers masked

Storage is in memory and seeded at start, so every sandbox begins clean.
"""

from __future__ import annotations

import asyncio
import base64
import contextvars
import hashlib
import hmac
import json
import logging
import os
import re
import sys
import time
import uuid
from collections import deque
from datetime import UTC, datetime
from enum import StrEnum

import driver_directory
from fastapi import Depends, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from starlette.exceptions import HTTPException as StarletteHTTPException

# --------------------------------------------------------------------------- config

SEED = os.environ.get("SEED_TEST_DATA", "true").lower() == "true"
# Test-only endpoints are registered only when this is on. Off by default; the GKE sandbox
# deployment turns it on. Never on in UAT or production.
TEST_HOOKS = os.environ.get("ENABLE_TEST_HOOKS", "false").lower() == "true"
# Demo sign-in only (standards/aaa.md): production uses the company identity provider.
SECRET = os.environ.get("DEMO_AUTH_SECRET", "demo-only-not-a-secret").encode()
TOKEN_TTL_S = 8 * 3600
# Release identity (deploy/prod): which build answered, and whether it is the stable or the
# canary copy. Sent on every response so a canary can be measured on its own (standards/slo.md).
APP_VERSION = os.environ.get("APP_VERSION", "dev")
APP_TRACK = os.environ.get("APP_TRACK", "")

app = FastAPI(title="Roadside Assistance API", version="1.0.0")

# --------------------------------------------------------------------------- logging

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
# Phone-shaped values: "+1 555 010 2233", "(555) 014-8392", "555-010-2233", "5550102233". Not dates or IDs.
PHONE = re.compile(r"\+\d[\d\s-]{8,}\d|(?:\(\d{3}\)|\b\d{3})[\s-]?\d{3}[\s-]?\d{4}\b")
RECENT_LOGS: deque[dict] = deque(maxlen=200)  # exposed only through a test hook

log = logging.getLogger("roadside")
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler(sys.stdout))
log.propagate = False


def mask(value: str) -> str:
    """Keep the last 2 digits of a phone number: +1 555 010 1234 -> ********34."""
    digits = re.sub(r"\D", "", value)
    return "*" * max(len(digits) - 2, 0) + digits[-2:]


def _scrub(value):
    """Mask phone numbers anywhere inside a logged value."""
    if isinstance(value, str):
        return PHONE.sub(lambda m: mask(m.group(0)), value)
    if isinstance(value, dict):
        return {
            k: (mask(v) if k in ("phone", "driver_phone") and isinstance(v, str) else _scrub(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    return value


def emit(event: str, **fields) -> None:
    """One JSON object per line (standards/logging.md). Phone numbers never appear in clear."""
    record = {
        "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
        "severity": fields.pop("severity", "INFO"),
        "event": event,
        "request_id": request_id_var.get(),
        **_scrub(fields),
    }
    RECENT_LOGS.append(record)
    log.info(json.dumps(record, default=str))


# --------------------------------------------------------------------------- errors


def error(status: int, code: str, message: str, **extra) -> JSONResponse:
    body = {"code": code, "message": message, "request_id": request_id_var.get(), **extra}
    return JSONResponse(status_code=status, content=body)


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


@app.exception_handler(ApiError)
async def api_error(_: Request, exc: ApiError):
    return error(exc.status, exc.code, exc.message)


def _field_path(loc: tuple) -> str:
    """('body', 'items', 0, 'qty') -> 'items[0].qty'"""
    out = ""
    for part in loc:
        if part == "body":
            continue
        out += f"[{part}]" if isinstance(part, int) else (f".{part}" if out else str(part))
    return out


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    errors = [{"field": _field_path(e["loc"]), "message": e["msg"]} for e in exc.errors()]
    return error(422, "VALIDATION_ERROR", "Request is invalid", errors=errors)


@app.exception_handler(StarletteHTTPException)
async def http_error(_: Request, exc: StarletteHTTPException):
    code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "HTTP_ERROR")
    return error(exc.status_code, code, str(exc.detail))


# --------------------------------------------------------------------------- request middleware


@app.middleware("http")
async def request_context(request: Request, call_next):
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex
    token = request_id_var.set(rid)
    start = time.perf_counter()
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        response.headers["X-App-Version"] = APP_VERSION
        if APP_TRACK:
            response.headers["X-App-Track"] = APP_TRACK
        if request.url.path != "/healthz":
            emit(
                "http.request",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=round((time.perf_counter() - start) * 1000, 1),
                user=getattr(request.state, "user", None),
                role=getattr(request.state, "role", None),
                version=APP_VERSION,
                track=APP_TRACK or None,
            )
        return response
    finally:
        request_id_var.reset(token)


# --------------------------------------------------------------------------- authentication

USERS = {
    "alice": {"name": "Alice Ng", "role": "member"},
    "bob": {"name": "Bob Ortiz", "role": "member"},
    "dana": {"name": "Dana Kim", "role": "dispatcher"},
}


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def sign(sub: str, role: str) -> str:
    payload = _b64(json.dumps({"sub": sub, "role": role, "exp": int(time.time()) + TOKEN_TTL_S}).encode())
    sig = _b64(hmac.new(SECRET, payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}"


def verify(token: str) -> dict | None:
    try:
        payload, sig = token.split(".")
        expected = _b64(hmac.new(SECRET, payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        return claims if claims.get("exp", 0) > time.time() else None
    except (ValueError, json.JSONDecodeError):
        return None


async def current_user(request: Request, authorization: str | None = Header(default=None)) -> dict:
    """Authentication: every /v1 endpoint (except sign-in) requires a valid bearer token."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ApiError(401, "UNAUTHENTICATED", "Sign in required")
    claims = verify(authorization.split(" ", 1)[1].strip())
    if not claims:
        raise ApiError(401, "UNAUTHENTICATED", "Invalid or expired token")
    request.state.user, request.state.role = claims["sub"], claims["role"]
    return claims


def require(*roles: str):
    """Authorization: deny by default; only the listed roles may call the endpoint."""

    async def check(user: dict = Depends(current_user)) -> dict:
        if user["role"] not in roles:
            raise ApiError(403, "FORBIDDEN", "Your role may not do this")
        return user

    return check


class DemoLogin(BaseModel):
    user: str


@app.post("/v1/auth/demo-login")
def demo_login(body: DemoLogin):
    """Demo sign-in: pick a seeded user. Stands in for the company identity provider."""
    u = USERS.get(body.user)
    if not u:
        raise ApiError(404, "USER_NOT_FOUND", f"Unknown demo user {body.user}")
    audit("auth.signed_in", actor=body.user, target=body.user)
    return {"token": sign(body.user, u["role"]), "user": body.user, "name": u["name"], "role": u["role"]}


@app.get("/v1/me")
async def me(user: dict = Depends(current_user)):
    u = USERS[user["sub"]]
    return {"user": user["sub"], "name": u["name"], "role": user["role"]}


# --------------------------------------------------------------------------- accounting (audit)

AUDIT: list[dict] = []


def audit(event: str, actor: str, target: str, **details) -> None:
    """Accounting: who did what to which record, when. Also written to the log."""
    entry = {
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "event": event,
        "actor": actor,
        "target": target,
        "request_id": request_id_var.get(),
        **details,
    }
    AUDIT.append(entry)
    emit("audit", audit_event=event, actor=actor, target=target, **details)


@app.get("/v1/audit")
def audit_log(event: str | None = None, target: str | None = None, _: dict = Depends(require("dispatcher"))):
    rows = [a for a in AUDIT if (not event or a["event"] == event) and (not target or a["target"] == target)]
    return list(reversed(rows))[:200]


# --------------------------------------------------------------------------- domain


class HelpType(StrEnum):
    tow = "tow"
    battery = "battery"
    flat_tyre = "flat_tyre"
    lockout = "lockout"
    fuel = "fuel"


STATUSES = ["received", "assigned", "en_route", "arrived", "completed"]
REQUESTS: dict[str, dict] = {}
RATINGS: dict[str, dict] = {}


class RatingTag(StrEnum):
    on_time = "on_time"
    friendly_driver = "friendly_driver"
    explained_fix = "explained_fix"


class ModerationStatus(StrEnum):
    approved = "approved"
    rejected = "rejected"


MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def current_month() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


def seed() -> None:
    REQUESTS.clear()
    RATINGS.clear()
    AUDIT.clear()
    r = {
        "id": "RSA-1001",
        "member": "bob",
        "type": "battery",
        "location": "I-80 eastbound, mile 42",
        "phone": "+1 555 010 2233",
        "status": "assigned",
        "eta_minutes": 25,
        "driver": "Sam (Truck 12)",
        "driver_name": "Sam",
        "driver_truck": "Truck 12",
        "driver_rating": 4.8,
        "driver_phone": "(555) 010-1212",
        "history": [{"status": "received", "at": now()}, {"status": "assigned", "at": now()}],
        "created_at": now(),
    }
    REQUESTS[r["id"]] = r


if SEED:
    seed()


def new_id() -> str:
    return f"RSA-{uuid.uuid4().hex[:6].upper()}"


def visible(r: dict, user: dict) -> bool:
    return user["role"] == "dispatcher" or r["member"] == user["sub"]


# --------------------------------------------------------------------------- RSA-001 request help


class HelpRequestIn(BaseModel):
    type: HelpType
    location: str = Field(min_length=3, max_length=200)
    phone: str

    @field_validator("phone")
    @classmethod
    def phone_format(cls, v: str) -> str:
        if not re.fullmatch(r"\+?[\d\s-]{10,20}", v) or len(re.sub(r"\D", "", v)) < 10:
            raise ValueError("phone must have 10 to 15 digits")
        return v


@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"ok": True}


@app.post("/v1/requests", status_code=201)
async def create_request(body: HelpRequestIn, user: dict = Depends(require("member"))):
    r = {
        "id": new_id(),
        "member": user["sub"],
        "type": body.type.value,
        "location": body.location,
        "phone": body.phone,
        "status": "received",
        "eta_minutes": None,
        "driver": None,
        "driver_name": None,
        "driver_truck": None,
        "driver_rating": None,
        "driver_phone": None,
        "history": [{"status": "received", "at": now()}],
        "created_at": now(),
    }
    REQUESTS[r["id"]] = r
    audit("request.created", actor=user["sub"], target=r["id"], type=r["type"])
    return r


# --------------------------------------------------------------------------- RSA-002 view requests


@app.get("/v1/requests")
async def list_requests(user: dict = Depends(require("member", "dispatcher"))):
    rows = [
        {**r, "rating": _public_rating(RATINGS[r["id"]]) if r["id"] in RATINGS else None}
        for r in REQUESTS.values()
        if visible(r, user)
    ]
    return sorted(rows, key=lambda r: r["created_at"], reverse=True)


# RSA-005: cache partner lookups (5 min TTL) so request details stays within SLO budget (≤ 300 ms).
_VERIFICATION_CACHE: dict[str, tuple[bool, float]] = {}
_VERIFICATION_TTL_S = 300.0


async def _is_driver_verified(driver_name: str) -> bool:
    now_mono = time.monotonic()
    cached = _VERIFICATION_CACHE.get(driver_name)
    if cached is not None and now_mono < cached[1]:
        return cached[0]
    profile = await asyncio.to_thread(driver_directory.lookup, driver_name)
    verified = profile["verified"] if profile else False
    _VERIFICATION_CACHE[driver_name] = (verified, now_mono + _VERIFICATION_TTL_S)
    return verified


@app.get("/v1/requests/{request_id}")
async def get_request(request_id: str, user: dict = Depends(require("member", "dispatcher"))):
    r = REQUESTS.get(request_id)
    if not r or not visible(r, user):  # never reveal that someone else's request exists
        raise ApiError(404, "REQUEST_NOT_FOUND", "Request not found")
    # RSA-005: is the assigned driver verified by the partner Driver Directory?
    name = r.get("driver_name")
    verified = await _is_driver_verified(name) if name else None
    rating = _public_rating(RATINGS[request_id]) if request_id in RATINGS else None
    return {**r, "driver_verified": verified, "rating": rating}


# --------------------------------------------------------------------------- RSA-003 dispatcher update


class UpdateIn(BaseModel):
    status: str | None = None
    eta_minutes: int | None = Field(default=None, ge=0, le=600)
    driver: str | None = Field(default=None, max_length=80)
    driver_name: str | None = Field(default=None, max_length=80)
    driver_truck: str | None = Field(default=None, max_length=120)
    driver_rating: float | None = Field(default=None, ge=1.0, le=5.0)
    driver_phone: str | None = Field(default=None, max_length=30)


@app.patch("/v1/requests/{request_id}")
async def update_request(request_id: str, body: UpdateIn, user: dict = Depends(require("dispatcher"))):
    r = REQUESTS.get(request_id)
    if not r:
        raise ApiError(404, "REQUEST_NOT_FOUND", "Request not found")
    changes = body.model_dump(exclude_none=True)
    if "status" in changes:
        new, cur = changes["status"], r["status"]
        if new not in STATUSES or STATUSES.index(new) != STATUSES.index(cur) + 1:
            raise ApiError(409, "INVALID_TRANSITION", f"Cannot move from {cur} to {new}")
        r["history"].append({"status": new, "at": now()})
    r.update(changes)
    audit("request.updated", actor=user["sub"], target=request_id, changes=changes)
    return r


# --------------------------------------------------------------------------- RSA-004 member cancel


CANCELLABLE_STATUSES = {"received", "assigned", "en_route"}


@app.post("/v1/requests/{request_id}/cancel")
async def cancel_request(request_id: str, user: dict = Depends(require("member"))):
    r = REQUESTS.get(request_id)
    if not r or r["member"] != user["sub"]:
        raise ApiError(404, "REQUEST_NOT_FOUND", "Request not found")
    if r["status"] not in CANCELLABLE_STATUSES:
        raise ApiError(409, "INVALID_TRANSITION", f"Cannot cancel request in status {r['status']}")
    prev = r["status"]
    r["status"] = "cancelled"
    r["history"].append({"status": "cancelled", "at": now()})
    audit("request.cancelled", actor=user["sub"], target=request_id, previous_status=prev)
    return r


# --------------------------------------------------------------------------- RSA-006 rate my rescue


def _driver_info(r: dict) -> tuple[str, str, str] | None:
    """Return (driver_key, first_name_only, truck) for a request, or None if unassigned."""
    raw_name = (r.get("driver_name") or "").strip()
    extracted_truck = ""
    if not raw_name:
        raw_driver = (r.get("driver") or "").strip()
        if not raw_driver:
            return None
        match = re.match(r"^([^(]+?)(?:\s*\(([^)]+)\))?$", raw_driver)
        raw_name = match.group(1).strip() if match else raw_driver
        extracted_truck = match.group(2).strip() if match and match.group(2) else ""
    if not raw_name:
        return None
    first_name = raw_name.split()[0]
    truck = (r.get("driver_truck") or extracted_truck).strip()
    return raw_name.lower(), first_name, truck


def _public_rating(entry: dict) -> dict:
    return {
        "request_id": entry["request_id"],
        "driver_display_name": entry["driver_display_name"],
        "driver_truck": entry["driver_truck"],
        "stars": entry["stars"],
        "tags": list(entry["tags"]),
        "comment": entry["comment"],
        "moderation_status": entry["moderation_status"],
        "created_at": entry["created_at"],
    }


def _compute_leaderboard(month: str, tag_filter: RatingTag | None = None) -> dict:
    grouped: dict[str, dict] = {}
    for entry in RATINGS.values():
        if entry["month"] != month:
            continue
        key = entry["driver_key"]
        bucket = grouped.setdefault(
            key,
            {
                "driver_key": key,
                "driver_display_name": entry["driver_display_name"],
                "driver_truck": entry["driver_truck"],
                "stars_sum": 0,
                "rating_count": 0,
                "tag_counts": {t.value: 0 for t in RatingTag},
                "approved_comments": [],
            },
        )
        if entry["driver_truck"]:
            bucket["driver_truck"] = entry["driver_truck"]
        bucket["stars_sum"] += entry["stars"]
        bucket["rating_count"] += 1
        for tag in entry["tags"]:
            bucket["tag_counts"][tag] = bucket["tag_counts"].get(tag, 0) + 1
        if entry["moderation_status"] == ModerationStatus.approved.value and entry["comment"]:
            bucket["approved_comments"].append(entry["comment"])

    drivers = []
    for bucket in grouped.values():
        if tag_filter and bucket["tag_counts"].get(tag_filter.value, 0) == 0:
            continue
        drivers.append(
            {
                "driver_key": bucket["driver_key"],
                "driver_display_name": bucket["driver_display_name"],
                "driver_truck": bucket["driver_truck"],
                "average_stars": round(bucket["stars_sum"] / bucket["rating_count"], 2),
                "rating_count": bucket["rating_count"],
                "tag_counts": bucket["tag_counts"],
                "approved_comments": bucket["approved_comments"],
            }
        )

    drivers.sort(key=lambda d: (-d["average_stars"], -d["rating_count"], d["driver_display_name"].lower()))
    total_ratings = sum(d["rating_count"] for d in drivers)
    weighted_sum = sum(grouped[d["driver_key"]]["stars_sum"] for d in drivers)
    fleet_avg = round(weighted_sum / total_ratings, 2) if total_ratings else 0.0

    public_drivers = [
        {
            "rank": idx,
            "driver_display_name": d["driver_display_name"],
            "driver_truck": d["driver_truck"],
            "average_stars": d["average_stars"],
            "rating_count": d["rating_count"],
            "tag_counts": d["tag_counts"],
            "approved_comments": d["approved_comments"],
        }
        for idx, d in enumerate(drivers, start=1)
    ]
    return {
        "month": month,
        "fleet_average_stars": fleet_avg,
        "total_ratings": total_ratings,
        "drivers": public_drivers,
    }


def _driver_monthly_stats(driver_key: str, month: str) -> tuple[float, int]:
    stars = [e["stars"] for e in RATINGS.values() if e["driver_key"] == driver_key and e["month"] == month]
    return (round(sum(stars) / len(stars), 2), len(stars)) if stars else (0.0, 0)


class RatingIn(BaseModel):
    stars: int = Field(ge=1, le=5)
    tags: list[RatingTag] = Field(default_factory=list)
    comment: str | None = Field(default=None, max_length=300)


class RatingModerationIn(BaseModel):
    moderation_status: ModerationStatus


@app.post("/v1/requests/{request_id}/rating", status_code=201)
async def create_rating(request_id: str, body: RatingIn, user: dict = Depends(require("member"))):
    r = REQUESTS.get(request_id)
    if not r or r["member"] != user["sub"]:  # AAA-7: never reveal another member's request
        raise ApiError(404, "REQUEST_NOT_FOUND", "Request not found")
    if request_id in RATINGS:
        raise ApiError(409, "ALREADY_RATED", "This request has already been rated")
    driver_info = _driver_info(r)
    if r["status"] != "completed" or driver_info is None:
        raise ApiError(409, "INVALID_TRANSITION", "Only completed requests with an assigned driver can be rated")

    driver_key, display_name, truck = driver_info
    dedup_tags = list(dict.fromkeys(t.value for t in body.tags))
    cleaned_comment = body.comment.strip() if body.comment and body.comment.strip() else None
    month = current_month()

    entry = {
        "request_id": request_id,
        "driver_key": driver_key,
        "driver_display_name": display_name,
        "driver_truck": truck,
        "stars": body.stars,
        "tags": dedup_tags,
        "comment": cleaned_comment,
        "moderation_status": "pending" if cleaned_comment else "none",
        "month": month,
        "created_at": now(),
    }
    RATINGS[request_id] = entry

    # LOG-4: free-text comment is omitted from audit and structured logs to avoid leaking personal data.
    audit(
        "rating.created",
        actor=user["sub"],
        target=request_id,
        driver=display_name,
        stars=body.stars,
        tags=dedup_tags,
        has_comment=cleaned_comment is not None,
    )
    avg, count = _driver_monthly_stats(driver_key, month)
    return {**_public_rating(entry), "driver_monthly_average": avg, "driver_monthly_count": count}


@app.patch("/v1/requests/{request_id}/rating")
async def moderate_rating(request_id: str, body: RatingModerationIn, user: dict = Depends(require("dispatcher"))):
    if request_id not in REQUESTS:
        raise ApiError(404, "REQUEST_NOT_FOUND", "Request not found")
    rating = RATINGS.get(request_id)
    if not rating:
        raise ApiError(404, "RATING_NOT_FOUND", "No rating found for this request")
    if rating["moderation_status"] == "none":
        raise ApiError(409, "INVALID_TRANSITION", "Cannot moderate a rating without a comment")

    rating["moderation_status"] = body.moderation_status.value
    audit(
        "rating.moderated",
        actor=user["sub"],
        target=request_id,
        moderation_status=body.moderation_status.value,
    )
    return _public_rating(rating)


@app.get("/v1/leaderboard/drivers")
async def driver_leaderboard(
    month: str | None = None,
    tag: RatingTag | None = None,
    _: dict = Depends(require("member", "dispatcher")),
):
    target_month = month or current_month()
    if not MONTH_RE.fullmatch(target_month):
        return error(
            422,
            "VALIDATION_ERROR",
            "Request is invalid",
            errors=[{"field": "month", "message": "month must match YYYY-MM"}],
        )
    return _compute_leaderboard(target_month, tag)


# --------------------------------------------------------------------------- test hooks (sandbox only)

if TEST_HOOKS:

    @app.get("/test/logs", include_in_schema=False)
    def recent_logs(limit: int = 50):
        """Recent structured log lines, so acceptance tests can check standards/logging.md."""
        return list(RECENT_LOGS)[-limit:]
