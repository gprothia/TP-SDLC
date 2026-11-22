---
id: RSA-003
title: Dispatcher updates a request
status: implemented
owner: "@gprothia"
issue: "#4"
---

# RSA-003: Dispatcher updates a request

## Why
Dispatchers move each request along (truck assigned, on the way, arrived, completed) and tell
the member when help will arrive.

## Scope
- In: next status, ETA in minutes, driver name.
- Out: assigning trucks automatically, notifications.

## Acceptance criteria

### RSA-003-AC1 [api]
- **Given** a request in status `received`
- **When** a dispatcher sends `PATCH /v1/requests/{id}` with status `assigned`, `eta_minutes` 20 and a driver
- **Then** the response is `200` with those values, and `history` ends with status `assigned`

### RSA-003-AC2 [api]
- **Given** a request in status `received`
- **When** a dispatcher sends status `en_route` (skipping `assigned`)
- **Then** the response is `409` with code `INVALID_TRANSITION`

### RSA-003-AC3 [api]
- **Given** a signed-in member
- **When** they send `PATCH /v1/requests/{id}` for their own request
- **Then** the response is `403` with code `FORBIDDEN`

### RSA-003-AC4 [api]
- **Given** a dispatcher updates a request
- **Then** the audit log has a `request.updated` event with the dispatcher as actor and the changes

### RSA-003-AC5 [ui]
- **Given** Alice sent a request and Dana (dispatcher) opens it
- **When** Dana saves "Truck assigned" with ETA 20 and driver "Sam (Truck 12)"
- **Then** Alice's page for that request shows "Truck assigned", "20 min" and "Sam (Truck 12)"

## Security & access (AAA)

### Authentication
Signed-in users only.

### Authorization
| Action | Roles allowed |
|---|---|
| Update status, ETA, driver | dispatcher |

### Accounting
| Audit event | When | Details recorded |
|---|---|---|
| `request.updated` | A dispatcher saves an update | actor, target (request id), changes |

## Logging
Standard `http.request` line; the audit event is logged too.

## API contract
| Method | Path | Success | Errors |
|---|---|---|---|
| PATCH | /v1/requests/{id} | 200 | 401, 403, 404, 409 INVALID_TRANSITION, 422 |

## SLO
```slo
p95_latency_ms: 300
error_rate_pct: 1.0
```

## Edge cases & errors
- ETA outside 0–600 minutes: `422` for field `eta_minutes`.

## Test data
Statuses in order: received, assigned, en_route, arrived, completed.

## Open questions
- [x] Can a status go backwards? → No.
