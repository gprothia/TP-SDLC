---
id: RSA-002
title: View requests
status: implemented
owner: "@gprothia"
issue: "#3"
---

# RSA-002: View requests

## Why
Members want to see their requests; dispatchers need to see every open request.

## Scope
- In: a list of requests (members: their own; dispatchers: all) and a detail view.
- Out: search, filters, maps.

## Acceptance criteria

### RSA-002-AC1 [api]
- **Given** member Alice has a request and Bob has request `RSA-1001`
- **When** Alice calls `GET /v1/requests`
- **Then** the response is `200`, includes her request, and does not include `RSA-1001`

### RSA-002-AC2 [api]
- **Given** a signed-in dispatcher
- **When** they call `GET /v1/requests`
- **Then** the response includes `RSA-1001` and requests from other members

### RSA-002-AC3 [api]
- **Given** member Alice
- **When** she calls `GET /v1/requests/RSA-1001` (Bob's)
- **Then** the response is `404` with code `REQUEST_NOT_FOUND`

### RSA-002-AC4 [ui]
- **Given** Alice is signed in
- **When** she opens **My requests**
- **Then** the table "Requests" does not show `RSA-1001`

### RSA-002-AC5 [ui]
- **Given** Dana (dispatcher) is signed in
- **When** she opens **All requests**
- **Then** the table shows `RSA-1001` with member `bob`

## Security & access (AAA)

### Authentication
Signed-in users only.

### Authorization
| Action | Roles allowed |
|---|---|
| List and view own requests | member |
| List and view all requests | dispatcher |

### Accounting
None: reading does not change data. (Reads of personal data may be audited in a later feature.)

## Logging
Standard `http.request` line.

## API contract
| Method | Path | Success | Errors |
|---|---|---|---|
| GET | /v1/requests | 200 | 401 |
| GET | /v1/requests/{id} | 200 | 401, 404 REQUEST_NOT_FOUND |

## SLO
```slo
p95_latency_ms: 300
error_rate_pct: 1.0
```

## Edge cases & errors
- Unknown id: `404` (same as someone else's, per standards/aaa.md AAA-7).

## Test data
Seeded request `RSA-1001`: Bob, battery, status assigned, ETA 25 min, driver "Sam (Truck 12)".

## Open questions
- [x] Newest first? → Yes.
