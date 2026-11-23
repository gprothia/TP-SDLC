---
id: RSA-006
title: Rate my rescue and top drivers leaderboard
status: approved
owner: "@gprothia"
issue: "#5"
---

# RSA-006: Rate my rescue and top drivers leaderboard

## Why
Members have no quick way to share feedback after a roadside rescue, and high-performing drivers do not receive visible recognition. Adding a lightweight 1–5 star rating flow for completed rescues and a monthly driver leaderboard for signed-in users lets members celebrate great service without a long survey.

## Scope
- In: submitting a final 1–5 star rating (with optional praise tags `On time`, `Friendly driver`, `Explained the fix` and an optional comment up to 300 characters) on a member's own `completed` rescue; thank-you confirmation with the driver's updated monthly average; a signed-in "Top drivers this month" leaderboard with driver portrait photos, full names, review counts, tag filters, and recent anonymous member quotes.
- Out: rating rescues while `en_route` or in any non-`completed` status; editing or deleting a submitted rating; unauthenticated/public leaderboard access; comment moderation workflows.

## Acceptance criteria

### RSA-006-AC1 [api]
- **Given** Alice is signed in and has a `completed` request assigned to driver `Marcus Rivera` with no rating yet
- **When** she sends `POST /v1/requests/{id}/rating` with `{"stars": 5, "tags": ["On time", "Friendly driver"], "comment": "Swapped my flat in 12 minutes."}`
- **Then** the response is `201` with `rating.stars` `5`, `rating.tags` `["On time", "Friendly driver"]`, `rating.comment` `"Swapped my flat in 12 minutes."`, `rating.submitted_at`, and `driver_monthly_avg`

### RSA-006-AC2 [api]
- **Given** Alice is signed in and has a request in status `received`, `assigned`, `en_route`, `arrived`, or `cancelled`
- **When** she sends `POST /v1/requests/{id}/rating` with `{"stars": 5}`
- **Then** the response is `409` with `code` `INVALID_STATUS`

### RSA-006-AC3 [api]
- **Given** Alice is signed in and has a `completed` request that already has a submitted rating
- **When** she sends `POST /v1/requests/{id}/rating` with `{"stars": 4}`
- **Then** the response is `409` with `code` `ALREADY_RATED`

### RSA-006-AC4 [api]
- **Given** Alice is signed in and has an unrated `completed` request
- **When** she sends `POST /v1/requests/{id}/rating` with `stars` outside `1..5`, an unknown tag not in `["On time", "Friendly driver", "Explained the fix"]`, or a `comment` longer than `300` characters
- **Then** the response is `422` with `code` `VALIDATION_ERROR` and `errors` naming the invalid field (`stars`, `tags`, or `comment`)

### RSA-006-AC5 [api]
- **Given** a request `RSA-1001` owned by Bob and marked `completed`
- **When** an unauthenticated caller sends `POST /v1/requests/RSA-1001/rating`, member Alice sends `POST /v1/requests/RSA-1001/rating`, or dispatcher Dana sends `POST /v1/requests/RSA-1001/rating`
- **Then** the unauthenticated caller receives `401` `UNAUTHENTICATED`, member Alice receives `404` `REQUEST_NOT_FOUND`, and dispatcher Dana receives `403` `FORBIDDEN`

### RSA-006-AC6 [api]
- **Given** member Alice submits a rating on her `completed` request
- **When** the rating is recorded
- **Then** `GET /v1/audit` includes an event `rating.submitted` with `actor` `"alice"`, `target` set to the request ID, and `stars` and `driver_name` in the event details

### RSA-006-AC7 [api]
- **Given** a signed-in `member`
- **When** they send `GET /v1/drivers/leaderboard` (optionally with `?tag=On+time`)
- **Then** the response is `200` with `month`, `fleet_avg_stars`, `total_ratings`, and `drivers` (only drivers with `rating_count >= 1`) ordered by `avg_stars` descending (each item containing `driver_name`, `truck`, `photo_url`, `avg_stars`, `rating_count`, `tag_counts`, and `latest_quote`); an unauthenticated caller receives `401` `UNAUTHENTICATED`, and a `dispatcher` receives `403` `FORBIDDEN`

### RSA-006-AC8 [ui]
- **Given** Alice is signed in and has an unrated `completed` request
- **When** she opens `/requests/{id}/rate`, selects `5` stars, toggles `On time`, enters `"Great rescue!"`, and clicks **Submit rating**
- **Then** she sees `Thank you!`, `5 out of 5 stars`, the tag `On time`, `"Great rescue!"`, and the driver's updated monthly average (`★ ... avg`)

### RSA-006-AC9 [ui]
- **Given** Alice is signed in
- **When** she opens `/requests/{id}/rate` for an `en_route` request or for a `completed` request she has already rated
- **Then** the `en_route` page shows `Ratings open once your rescue is completed` with no submit button, and the already-rated page shows her submitted rating read-only with no edit button

### RSA-006-AC10 [ui]
- **Given** an unauthenticated visitor or a signed-in user
- **When** the unauthenticated visitor opens `/leaderboard`, or the signed-in user opens `/leaderboard` and clicks the `On time` filter
- **Then** the unauthenticated visitor is redirected to `/signin`, and the signed-in user sees `Top drivers this month`, driver portrait photos, full names, average star ratings, review counts, recent member quotes, and the standings filtered to drivers with `On time` tags

## Security & access (AAA)

### Authentication
Every `/v1` endpoint requires `Authorization: Bearer <token>` (AAA-1). Signed-out visitors opening `/requests/{id}/rate` or `/leaderboard` are redirected to `/signin`; API calls without a valid token receive `401` `UNAUTHENTICATED`.

### Authorization
| Action | Roles allowed |
|---|---|
| Submit a rating (`POST /v1/requests/{id}/rating`) | member (owner only; `404` for others per AAA-7; `403` for dispatcher per AAA-5) |
| View driver leaderboard (`GET /v1/drivers/leaderboard`) | member (`403` for dispatcher per AAA-5; `401` when signed out per AAA-1) |

### Accounting
| Audit event | When | Details recorded |
|---|---|---|
| `rating.submitted` | A member submits a rating on a completed rescue | `actor`, `target` (request ID), `driver_name`, `stars`, `tags` |

## Logging
Standard `http.request` line (LOG-2) and `event: "audit"` line on `rating.submitted` (LOG-5). Request bodies (including comment text) are not logged (LOG-4); any phone-shaped values in logged strings are masked to the last two digits (`********34`, LOG-4).

## API contract
| Method | Path | Success | Errors |
|---|---|---|---|
| POST | /v1/requests/{id}/rating | 201 | 401 UNAUTHENTICATED, 403 FORBIDDEN, 404 REQUEST_NOT_FOUND, 409 INVALID_STATUS, 409 ALREADY_RATED, 422 VALIDATION_ERROR |
| GET | /v1/drivers/leaderboard | 200 | 401 UNAUTHENTICATED, 403 FORBIDDEN, 422 VALIDATION_ERROR |

## SLO
```slo
p95_latency_ms: 300
error_rate_pct: 1.0
```

## Prototype reference
Link: `prototypes/rate-my-rescue/` (from branch `proto/rate-my-rescue`)

| Screen / element | What the user sees or does | Data behind it | Became |
|---|---|---|---|
| Rescue list & status filter (`All` / `Completed` / `En route`) | Pick a rescue to rate; prototype allowed rating `en_route` rescues | `rescues` list with `status` | RSA-006-AC2, RSA-006-AC9 (restricted to `completed` only per #5) |
| Rating form (`How did we do?`, 5 stars, 3 praise tags, 300-char comment) | Select 1–5 stars, toggle `On time` / `Friendly driver` / `Explained the fix`, optional comment | `stars`, `tags`, `comment` | RSA-006-AC1, RSA-006-AC4, RSA-006-AC8 |
| Thank-you screen (`Thank you!`, receipt, `Edit this rating` button) | Shows submitted rating and updated driver monthly average; prototype allowed editing | `rating`, `driver_monthly_avg` | RSA-006-AC3, RSA-006-AC8, RSA-006-AC9 (editing removed; ratings final per #5) |
| Public `Top drivers this month` leaderboard & `Copy public link` | No-sign-in leaderboard with driver photos, full names, averages, review counts, tag filters, quotes | `drivers` standings, `tag_counts`, `latest_quote` | RSA-006-AC7, RSA-006-AC10 (sign-in required per AAA-1 & #5; `Copy public link` removed) |
| `Reset demo data` footer bar | Prototype-only local reset button | Local JS state | Not carried over (real API persistence) |

## Edge cases & errors
- Rescue has no assigned driver: cannot be rated (`409` `INVALID_STATUS`).
- Drivers with `0` ratings in the current month are omitted from the leaderboard.
- Tie-breaking on leaderboard: drivers with identical `avg_stars` are ordered by `rating_count` descending, then `driver_name` ascending.
- Unknown `?tag=` query parameter on `GET /v1/drivers/leaderboard`: returns `422` `VALIDATION_ERROR`.
- Comment containing only whitespace: trimmed and stored as `null` / empty so blank quotes do not overwrite a driver's `latest_quote`.

## Test data
Seeded users (`alice`, `bob` as members; `dana` as dispatcher) and seeded monthly driver ratings for demo drivers (`Marcus Rivera`, `Elena Brooks`, `Maria Santos`, `Sam Patel`, `Devon Clark`). Seeded request `RSA-1001` (Bob's) starts `assigned`; tests transition a request to `completed` (or create one) before rating.

## Open questions
- [x] (Business) Should `dispatcher` also be allowed to view `/leaderboard` and `GET /v1/drivers/leaderboard`, or only `member`? → Only `member` (`403 FORBIDDEN` for `dispatcher` per `AAA-5`).
- [x] (Business) Should drivers with 0 ratings this month appear on the leaderboard, or only drivers with at least 1 rating? → Only drivers with 1 or more ratings this month.
- [x] (IT / Security — LOG-4) Member comments appear as anonymous quotes on the signed-in leaderboard: should comments containing phone-shaped values be masked or rejected at submission? → Mask phone-shaped values in logs (`********34` per `LOG-4`).
- [x] (IT / Security — AAA-1) Should driver portrait images be served from the authenticated web app (with an initials fallback if a driver has no photo)? → Yes, served from the authenticated web app with an initials fallback if no photo is present.
