---
id: RSA-006
title: Rate My Rescue
status: implemented
owner: "@gprothia"
issue: "#9"
---

# RSA-006: Rate My Rescue

## Why
Members have no quick way to share feedback after a roadside rescue or recognize a driver who did a great job, and drivers lack visible monthly recognition for high member satisfaction. A fast rating flow and monthly leaderboard close that loop.

## Scope
- In: one-time rating (`1`–`5` stars, optional tags `On time`, `Friendly driver`, `Explained the fix`, optional comment up to `300` characters) on a member's own `completed` rescue; thank-you confirmation showing the submitted rating and updated driver average; signed-in `"Top drivers this month"` leaderboard showing driver name, photo, truck unit, rescue count, rating count, and average stars.
- Out: rating rescues that are not `completed` (e.g. `en_route`), editing a submitted rating, public/unauthenticated access to the leaderboard, and displaying member comments on the leaderboard.

## Acceptance criteria

### RSA-006-AC1 [api]
- **Given** Alice is signed in as a `member` and owns a request in status `completed` with an assigned driver and no existing rating
- **When** she sends `POST /v1/requests/{id}/rating` with `{"stars": 5, "tags": ["On time", "Friendly driver"], "comment": "Quick jump-start!"}`
- **Then** the response is `201` with `request_id`, `driver_name`, `stars` `5`, `tags` `["On time", "Friendly driver"]`, `comment` `"Quick jump-start!"`, and `created_at`

### RSA-006-AC2 [api]
- **Given** Alice is signed in as a `member` and owns a request in status `received`, `assigned`, `en_route`, `arrived`, or `cancelled`
- **When** she sends `POST /v1/requests/{id}/rating` with `{"stars": 5}`
- **Then** the response is `409` with code `INVALID_TRANSITION`

### RSA-006-AC3 [api]
- **Given** Alice is signed in as a `member` and owns a `completed` request that already has a rating
- **When** she sends `POST /v1/requests/{id}/rating` with `{"stars": 4}`
- **Then** the response is `409` with code `ALREADY_RATED`

### RSA-006-AC4 [api]
- **Given** Alice is signed in as a `member` and owns an unrated `completed` request
- **When** she sends `POST /v1/requests/{id}/rating` with `stars` `0` or `6`, an unknown tag, or a `comment` longer than `300` characters
- **Then** the response is `422` with code `VALIDATION_ERROR` and `errors` naming the invalid field (`stars`, `tags`, or `comment`)

### RSA-006-AC5 [api]
- **Given** Alice is signed in as a `member`
- **When** she sends `POST /v1/requests/RSA-1001/rating` (Bob's request)
- **Then** the response is `404` with code `REQUEST_NOT_FOUND`

### RSA-006-AC6 [api]
- **Given** Dana is signed in as a `dispatcher`
- **When** she sends `POST /v1/requests/{id}/rating`
- **Then** the response is `403` with code `FORBIDDEN`

### RSA-006-AC7 [api]
- **Given** a caller without a valid `Authorization: Bearer <token>` header
- **When** they send `POST /v1/requests/{id}/rating` or `GET /v1/drivers/leaderboard`
- **Then** the response is `401` with code `UNAUTHENTICATED`

### RSA-006-AC8 [api]
- **Given** a member submits a valid rating on a `completed` request
- **Then** the audit log contains a `rating.created` event with that member as `actor`, the request id as `target`, and `stars` and `tags` recorded

### RSA-006-AC9 [api]
- **Given** a signed-in `member` or `dispatcher`
- **When** they send `GET /v1/drivers/leaderboard`
- **Then** the response is `200` with `drivers` containing only drivers with `rating_count >= 5`, ordered by `average_stars` descending (then `rescue_count` descending), each item containing `driver_name`, `photo_url`, `truck_unit`, `rescue_count`, `rating_count`, and `average_stars`, and containing no member `comment` fields

### RSA-006-AC10 [ui]
- **Given** Alice is signed in and has an unrated `completed` request
- **When** she opens the rating page for that request, sees `"How did we do?"`, selects `5` stars, toggles `"On time"`, enters `"Great service"`, and clicks **Submit rating**
- **Then** she sees `"Thanks for your feedback!"`, her submitted `5` stars, `"On time"` tag, comment `"Great service"`, and the driver's updated monthly average

### RSA-006-AC11 [ui]
- **Given** Alice is signed in
- **When** she opens `/leaderboard`
- **Then** she sees `"Top drivers this month"` with each driver's photo, name, truck unit, rescue count, and average stars, and no member comments; a signed-out visitor opening `/leaderboard` is redirected to `/signin`

## Security & access (AAA)

### Authentication
Every `/v1` endpoint requires `Authorization: Bearer <token>` (AAA-1). Signed-out visitors opening the rating page or `/leaderboard` are redirected to `/signin`; API calls without a valid token receive `401` with code `UNAUTHENTICATED`.

### Authorization
| Action | Roles allowed |
|---|---|
| Submit rating on own completed request (`POST /v1/requests/{id}/rating`) | member (owner only; `404` for others per AAA-7; `403` for dispatcher per AAA-5) |
| View monthly driver leaderboard (`GET /v1/drivers/leaderboard`) | member, dispatcher |

### Accounting
| Audit event | When | Details recorded |
|---|---|---|
| `rating.created` | A member submits a rating on a completed request | `actor`, `target` (request id), `stars`, `tags` |

## Logging
Standard `http.request` line (LOG-2) and `event: "audit"` line on `rating.created` (LOG-5). Request bodies and free-text `comment` values are never logged in clear (LOG-4).

## API contract
| Method | Path | Success | Errors |
|---|---|---|---|
| POST | /v1/requests/{id}/rating | 201 | 401 UNAUTHENTICATED, 403 FORBIDDEN, 404 REQUEST_NOT_FOUND, 409 INVALID_TRANSITION, 409 ALREADY_RATED, 422 VALIDATION_ERROR |
| GET | /v1/drivers/leaderboard | 200 | 401 UNAUTHENTICATED |

## SLO
```slo
p95_latency_ms: 300
error_rate_pct: 1.0
```

## Prototype reference
Link: `prototypes/rate-my-rescue/` (from branch `proto/rate-my-rescue`)

| Screen / element | What the user sees or does | Data behind it | Became |
|---|---|---|---|
| Rescue list & status filter | Lists member's rescues (`completed` and `en_route`) with "Rate rescue" / "Edit rating" buttons | `requests` owned by signed-in member; only `completed` and unrated allowed per #9 | RSA-006-AC2, RSA-006-AC3 |
| `"How did we do?"` rating form | 1–5 star buttons, tags (`On time`, `Friendly driver`, `Explained the fix`), 300-char comment box, Submit button | `stars` (1–5), `tags` (enum), `comment` (optional, max 300 chars, escaped per SEC-10) | RSA-006-AC1, RSA-006-AC4, RSA-006-AC10 |
| Thank-you screen | `"Thanks for your feedback!"`, submitted stars/tags/comment, updated driver monthly average, link to leaderboard | Submitted rating + updated driver `average_stars` and `rating_count` | RSA-006-AC10 |
| `"Top drivers this month"` leaderboard | Ranked list with driver photo, name, truck unit, rescue count, average stars; prototype had it public with member quotes | Driver aggregates; requires sign-in (AAA-1) and omits member comments per #9 | RSA-006-AC7, RSA-006-AC9, RSA-006-AC11 |

## Edge cases & errors
- Submitting a rating without selecting 1–5 stars: `422` `VALIDATION_ERROR` for field `stars` (and client-side validation message in the UI).
- Whitespace-only `comment` values are normalized to `null` (empty), and comments longer than `300` characters return `422` `VALIDATION_ERROR` for field `comment`.
- Submitting a comment containing HTML characters (e.g. `<script>`): stored safely and HTML-escaped on render (`SEC-10`).
- Rating a rescue that has no assigned driver yet: rejected with `409` `INVALID_TRANSITION`.
- Drivers with fewer than `5` ratings are excluded from `GET /v1/drivers/leaderboard`.

## Test data
- Seeded users: `alice`, `bob` (`member`), `dana` (`dispatcher`).
- Allowed tags: `On time`, `Friendly driver`, `Explained the fix`.
- Seeded completed rescue for `alice` (or created via `POST /v1/requests` + dispatcher transitions to `completed`) and `RSA-1001` owned by `bob`.
- Seeded drivers with `rating_count >= 5` so the leaderboard returns ranked entries.

## Open questions
- [x] **Business:** What should the minimum number of ratings be for a driver to appear on "Top drivers this month" (e.g. at least 1 rating, or 5+)? → `5+` (`rating_count >= 5`) (#9)
- [x] **Business:** When two drivers have the same `average_stars`, should ties be broken by `rating_count` descending (as in the prototype) or `rescue_count` descending? → `rescue_count` descending (#9)
- [x] **IT / security (SEC-10, LOG-4):** Should `comment` allow blank/whitespace-only strings to be normalized to `null` / empty, and is `300` characters the desired hard API limit? → Yes (#9)
