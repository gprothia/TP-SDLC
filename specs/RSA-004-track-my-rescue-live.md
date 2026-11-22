---
id: RSA-004
title: Live Track My Rescue
status: implemented
owner: "@gprothia"
issue: "#4"
---

# RSA-004: Live Track My Rescue

## Why
Stranded members waiting for roadside assistance need live visibility into their driver's ETA, progress, and location, plus quick actions to call, share, or cancel, to reduce anxiety and repeat support calls.

## Scope
- In: live ETA countdown (refreshing every 2 minutes), 4-step progress tracker (`received`, `assigned`, `en_route`, `arrived`), simple live map with truck position, driver details (name, truck, rating, phone), call driver action, copyable live tracking link (sign-in required), and member request cancellation.
- Out: unauthenticated public tracking links, masked/relay voice calling, live GPS hardware integration (uses API-provided progress/location).

## Acceptance criteria

### RSA-004-AC1 [ui]
- **Given** Alice is signed in and has an active request in status `en_route` with `eta_minutes` `14`
- **When** she opens the live tracking view for that request
- **Then** she sees the big ETA (`14 min away`), and the page polls `GET /v1/requests/{id}` every `120` seconds (`2 min`) for updates

### RSA-004-AC2 [ui]
- **Given** Alice is viewing her request in status `en_route`
- **When** she looks at the progress tracker
- **Then** she sees the 4 steps (`Received`, `Truck assigned`, `On the way`, `Arrived`) with `Received` and `Truck assigned` marked done and `On the way` marked active

### RSA-004-AC3 [ui]
- **Given** Alice is viewing her request in status `en_route`
- **When** the live map renders
- **Then** she sees her destination pin ("You") and the rescue truck marker positioned along the route

### RSA-004-AC4 [api,ui]
- **Given** a request has an assigned driver (`driver_name`, `driver_truck`, `driver_rating`, `driver_phone`)
- **When** the member calls `GET /v1/requests/{id}` or views the tracking page
- **Then** the API returns `200` with those driver fields and the UI displays the driver's name, truck, rating, and phone number

### RSA-004-AC5 [ui]
- **Given** Alice is viewing her request with an assigned driver
- **When** she clicks **Call Driver**
- **Then** she sees the driver's phone number ready to call

### RSA-004-AC6 [api,ui]
- **Given** Alice clicks **Share Live Link** on her tracking page
- **When** the link is copied and someone opens it without signing in (or calls `GET /v1/requests/{id}` without a token)
- **Then** the UI redirects to `/signin` and the API returns `401` with code `UNAUTHENTICATED`

### RSA-004-AC7 [api]
- **Given** member Alice has a request in status `received`, `assigned`, or `en_route`
- **When** she sends `POST /v1/requests/{id}/cancel`
- **Then** the response is `200` with `status` `cancelled`, and `history` ends with status `cancelled`

### RSA-004-AC8 [api]
- **Given** a request is already in status `arrived`, `completed`, or `cancelled`
- **When** the member sends `POST /v1/requests/{id}/cancel`
- **Then** the response is `409` with code `INVALID_TRANSITION`

### RSA-004-AC9 [api]
- **Given** member Alice
- **When** she sends `POST /v1/requests/RSA-1001/cancel` (Bob's request)
- **Then** the response is `404` with code `REQUEST_NOT_FOUND`

### RSA-004-AC10 [api]
- **Given** a signed-in dispatcher
- **When** they send `POST /v1/requests/{id}/cancel`
- **Then** the response is `403` with code `FORBIDDEN`

### RSA-004-AC11 [api]
- **Given** a member cancels their request
- **Then** the audit log has a `request.cancelled` event with that member as `actor` and the request id as `target`

### RSA-004-AC12 [ui]
- **Given** Alice is viewing her `en_route` request
- **When** she clicks **Cancel Rescue Request** and confirms in the dialog
- **Then** the page shows the request as `Cancelled`

## Security & access (AAA)

### Authentication
Every `/v1` endpoint requires `Authorization: Bearer <token>` (AAA-1). Signed-out visitors opening the tracking page or a shared live link are sent to `/signin`; API calls without a valid token receive `401` `UNAUTHENTICATED`.

### Authorization
| Action | Roles allowed |
|---|---|
| View own request live tracking (`GET /v1/requests/{id}`) | member (owner only; `404` for others per AAA-7), dispatcher |
| Cancel own request (`POST /v1/requests/{id}/cancel`) | member (owner only; `404` for others per AAA-7; `403` for dispatcher per AAA-5) |

### Accounting
| Audit event | When | Details recorded |
|---|---|---|
| `request.cancelled` | A member cancels a request | `actor`, `target` (request id), previous status |

## Logging
Standard `http.request` line (LOG-2) and `event: "audit"` line on cancellation (LOG-5). Driver phone numbers (`driver_phone`) are personal data and are never logged in clear (masked to last two digits, e.g. `********92`, per LOG-4).

## API contract
| Method | Path | Success | Errors |
|---|---|---|---|
| GET | /v1/requests/{id} | 200 | 401, 404 REQUEST_NOT_FOUND |
| POST | /v1/requests/{id}/cancel | 200 | 401, 403 FORBIDDEN, 404 REQUEST_NOT_FOUND, 409 INVALID_TRANSITION |

## SLO
```slo
p95_latency_ms: 300
error_rate_pct: 1.0
```

## Prototype reference
Link: `prototypes/track-my-rescue-live/` (from branch `proto/track-my-rescue-live`)

| Screen / element | What the user sees or does | Data behind it | Became |
|---|---|---|---|
| ETA hero card | Big ETA in minutes (`14 min away`), arrival estimate, live badge | `eta_minutes`, `status` (polled every 2 min) | RSA-004-AC1 |
| 4-step progress tracker | `Received`, `Truck assigned`, `On the way`, `Arrived` with timestamps | `status`, `history` | RSA-004-AC2 |
| Live SVG map | Destination pin ("You") and moving truck marker on route | `truck_progress` / `eta_minutes` | RSA-004-AC3 |
| Driver card | Name, truck, star rating, phone number | `driver_name`, `driver_truck`, `driver_rating`, `driver_phone` | RSA-004-AC4 |
| Call Driver button | Opens call modal / dialer with driver's phone | `driver_phone` (personal data; masked in logs per LOG-4) | RSA-004-AC5 |
| Share Live Link button | Copies live tracking URL to clipboard | Request tracking URL (requires sign-in per AAA-1 & AAA-7) | RSA-004-AC6 |
| Cancel Rescue Request button | Confirmation modal, cancels request | `POST /v1/requests/{id}/cancel` (`request.cancelled` audit) | RSA-004-AC7..AC12 |

## Edge cases & errors
- Cancelling a request that is `arrived`, `completed`, or already `cancelled`: `409` `INVALID_TRANSITION`.
- Unknown request id or another member's request: `404` `REQUEST_NOT_FOUND` (AAA-7).
- Dispatcher calling member cancel endpoint: `403` `FORBIDDEN` (AAA-5).

## Test data
Seeded request `RSA-1001`: Bob, battery, status `assigned`, ETA 25 min, driver `Sam (Truck 12)`, plus `driver_truck`, `driver_rating`, and `driver_phone` for live tracking tests.

## Open questions
- [x] (Business) Can a member cancel while `received` or `assigned` as well as `en_route`, and not once `arrived` or `completed`? → Yes, only when `received`, `assigned`, or `en_route` (not once `arrived` or `completed`).
- [x] (Business) Between the 2-minute server refreshes, should the UI tick down the ETA locally or only update on each 2-minute refresh? → Only update on each 2-minute refresh.
- [x] (IT / Security — AAA-1, AAA-7) Since the shared live link requires sign-in and `AAA-7` hides other members' requests (`404`), confirm the shared link is only viewable by the signed-in member (or a dispatcher), not another member's account. → Confirmed: shared link is only viewable by the signed-in member (or dispatcher).
- [x] (IT / Security — LOG-4) Confirm `driver_phone` is never logged in clear (masked to last 2 digits if ever logged). → Confirmed: `driver_phone` is never logged in clear.
