#!/usr/bin/env python3
"""Synthetic member traffic for canary releases (standards/slo.md SLO-3).

Runs as a pod next to the API (scripts/prod.sh measure, scripts/sandbox.sh load). It signs
in as the demo users and calls the API the way the apps do, for DURATION_S seconds. Every
request opens a new connection, so the Service spreads requests over all copies (about 10%
reach a 1-in-10 canary). Results are grouped by the X-App-Track response header.

Standard library only, so it runs in the API image without installing anything.

Env: API_BASE_URL (default http://api:8080), DURATION_S (180), WARMUP_S (10), WORKERS (12).
Prints one line "LOADGEN_RESULT {json}" at the end.
"""

from __future__ import annotations

import json
import os
import random
import threading
import time
import urllib.error
import urllib.request

BASE = os.environ.get("API_BASE_URL", "http://api:8080").rstrip("/")
DURATION_S = float(os.environ.get("DURATION_S", "180"))
WARMUP_S = float(os.environ.get("WARMUP_S", "10"))
WORKERS = int(os.environ.get("WORKERS", "12"))

# (weight, label, method, path, user, body): what members and dispatchers do most.
MIX = [
    (35, "GET /v1/requests/{id}", "GET", "/v1/requests/RSA-1001", "bob", None),
    (10, "GET /v1/requests/{id}", "GET", "/v1/requests/RSA-1001", "dana", None),
    (25, "GET /v1/requests", "GET", "/v1/requests", "alice", None),
    (15, "GET /v1/me", "GET", "/v1/me", "bob", None),
    (
        15,
        "POST /v1/requests",
        "POST",
        "/v1/requests",
        "alice",
        {"type": "tow", "location": "I-80 eastbound, mile 12", "phone": "+1 555 010 4455"},
    ),
]
WEIGHTS = [m[0] for m in MIX]


def call(method: str, path: str, token: str | None = None, body: dict | None = None) -> tuple[int, str, float]:
    """One request on a fresh connection. Returns (status, track, latency_ms)."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)  # noqa: S310 - fixed in-cluster URL
    req.add_header("Connection", "close")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            resp.read()
            status, track = resp.status, resp.headers.get("X-App-Track", "unknown")
    except urllib.error.HTTPError as e:
        status, track = e.code, e.headers.get("X-App-Track", "unknown")
    except OSError:
        status, track = 599, "unknown"  # timeout / connection failure counts as a server error
    return status, track, (time.perf_counter() - start) * 1000


def sign_in(user: str) -> str:
    for _ in range(30):
        req = urllib.request.Request(  # noqa: S310
            BASE + "/v1/auth/demo-login",
            data=json.dumps({"user": user}).encode(),
            method="POST",
            headers={"Content-Type": "application/json", "Connection": "close"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
                return json.loads(resp.read())["token"]
        except OSError:
            time.sleep(2)
    raise SystemExit(f"could not sign in as {user} at {BASE}")


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int(round(p / 100 * (len(ordered) - 1))))], 1)


def summarise(samples: list[tuple[str, str, int, float]]) -> dict:
    tracks: dict[str, dict] = {}
    for track in sorted({s[0] for s in samples} | {"all"}):
        rows = [s for s in samples if track in ("all", s[0])]
        endpoints = {}
        for label in sorted({r[1] for r in rows}):
            er = [r for r in rows if r[1] == label]
            endpoints[label] = {
                "count": len(er),
                "p95_ms": percentile([r[3] for r in er], 95),
                "error_pct": round(100 * sum(r[2] >= 500 for r in er) / len(er), 2),
            }
        lat = [r[3] for r in rows]
        tracks[track] = {
            "count": len(rows),
            "p50_ms": percentile(lat, 50),
            "p95_ms": percentile(lat, 95),
            "p99_ms": percentile(lat, 99),
            "error_pct": round(100 * sum(r[2] >= 500 for r in rows) / len(rows), 2) if rows else 0.0,
            "endpoints": endpoints,
        }
    return tracks


def main() -> None:
    tokens = {u: sign_in(u) for u in {m[4] for m in MIX}}
    samples: list[tuple[str, str, int, float]] = []
    lock = threading.Lock()
    t0 = time.monotonic()
    end = t0 + WARMUP_S + DURATION_S

    def worker() -> None:
        rnd = random.Random()  # noqa: S311 - traffic mix, not security
        while (now := time.monotonic()) < end:
            _, label, method, path, user, body = rnd.choices(MIX, WEIGHTS)[0]
            status, track, ms = call(method, path, tokens[user], body)
            if now - t0 >= WARMUP_S:
                with lock:
                    samples.append((track, label, status, ms))
            time.sleep(0.05)

    print(f"loadgen: {WORKERS} workers, {WARMUP_S:.0f}s warm-up + {DURATION_S:.0f}s measured against {BASE}")
    threads = [threading.Thread(target=worker, daemon=True) for _ in range(WORKERS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    result = {"duration_s": DURATION_S, "tracks": summarise(samples)}
    for track, r in result["tracks"].items():
        print(f"  {track:8} {r['count']:6} requests  p95 {r['p95_ms']:7.1f} ms  errors {r['error_pct']:.2f}%")
    print("LOADGEN_RESULT " + json.dumps(result))


if __name__ == "__main__":
    main()
