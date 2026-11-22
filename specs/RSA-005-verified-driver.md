---
id: RSA-005
title: Verified driver badge
status: implemented
owner: "@gprothia"
issue: "#9"
---

# RSA-005: Verified driver badge

## Why
Members waiting at the roadside are wary of strangers. Showing that the assigned driver is
verified by our partner (background and licence checked) reassures them before the truck arrives.

## Scope
- In: a `driver_verified` flag on a request's details, taken from the partner Driver Directory
  (`services/api/driver_directory.py`); a "Verified driver" badge on the tracking page.
- Out: showing the verification date or documents; dispatcher tools to request a re-check.

## Acceptance criteria

### RSA-005-AC1 [api]
- **Given** Bob's seeded request `RSA-1001` with driver `Sam`, whom the Driver Directory lists as verified
- **When** Bob sends `GET /v1/requests/RSA-1001`
- **Then** the response is `200` with `driver_verified` `true`

### RSA-005-AC2 [api]
- **Given** Alice's request assigned to driver `Marcus Rivera`, who is not verified in the Driver Directory
- **When** Alice sends `GET /v1/requests/{id}`
- **Then** the response is `200` with `driver_verified` `false`

### RSA-005-AC3 [api]
- **Given** Alice's new request with no driver assigned yet
- **When** Alice sends `GET /v1/requests/{id}`
- **Then** the response is `200` with `driver_verified` `null`

### RSA-005-AC4 [ui]
- **Given** Bob is signed in and his request `RSA-1001` has verified driver `Sam`
- **When** he opens `/requests/RSA-1001`
- **Then** the driver card shows the badge `Verified driver`

### RSA-005-AC5 [ui]
- **Given** Alice is signed in and her request's driver is not verified
- **When** she opens her request's page
- **Then** the driver card shows `Verification pending` and no `Verified driver` badge

## Security & access (AAA)

### Authentication
Unchanged: `GET /v1/requests/{id}` requires `Authorization: Bearer <token>` (AAA-1); `401` `UNAUTHENTICATED` without it.

### Authorization
| Action | Roles allowed |
|---|---|
| See a request's `driver_verified` (`GET /v1/requests/{id}`) | member (owner only; `404` for others per AAA-7), dispatcher |

### Accounting
None: reading a request changes nothing, so there is no audit event (AAA-9 covers changes only).

## Logging
Standard `http.request` line (LOG-2). The flag is not personal data; no new fields are logged.

## API contract
| Method | Path | Success | Errors |
|---|---|---|---|
| GET | /v1/requests/{id} | 200 (adds `driver_verified`: true, false or null) | 401, 404 REQUEST_NOT_FOUND |

## SLO
```slo
p95_latency_ms: 300
error_rate_pct: 1.0
```

## Edge cases & errors
- No driver assigned: `driver_verified` is `null` and the page shows no badge.
- A driver the directory doesn't know: `driver_verified` is `false` ("Verification pending").

## Test data
Seeded request `RSA-1001`: Bob, driver `Sam` (verified in the Driver Directory demo data).

## Open questions
- [x] (Business) Show "Verification pending" for unverified drivers, or nothing? → Show "Verification pending".
- [x] (IT / Security) Is the verification flag personal data? → No; it is a yes/no about the driver's checks, not about the member.
