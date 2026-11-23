---
id: RSA-006
title: Rate my rescue
status: approved
owner: "@gprothia"
issue: "#2"
---

# RSA-006: Rate my rescue

## Why
Members currently have no way to give quick feedback after a completed roadside rescue, and Marketing has no way to recognize top-performing drivers each month. A lightweight rating flow and signed-in monthly leaderboard capture member feedback right after completion while protecting member and driver privacy.

## Scope
- In: one-time member rating (1–5 stars, optional tags `On time`, `Friendly driver`, `Explained the fix`, optional comment up to 300 characters) on `completed` requests with an assigned driver; thank-you confirmation screen with updated driver monthly average; read-only rating display when revisiting a rated request; signed-in "Top drivers this month" leaderboard showing first name and truck (no photos or last names), average stars, rating counts, praise-tag counts, and dispatcher-moderated comments; dispatcher comment moderation (approve/reject).
- Out: rating non-completed rescues (`received`, `assigned`, `en_route`, `arrived`, `cancelled`) or requests with no assigned driver; editing or deleting a rating after submission; unauthenticated public leaderboard links; exposing driver photos or full names; automated profanity/AI moderation.

## Acceptance criteria

### RSA-006-AC1 [api]
- **Given** member Alice has a `completed` request assigned to driver `Sam` with no rating yet
- **When** Alice sends `POST /v1/requests/{id}/rating` with `stars` `5`, `tags` `["on_time", "friendly_driver"]`, and `comment` `"Arrived on time and changed the flat safely"`
- **Then** the response is `201` with `request_id` equal to that request's id, `stars` `5`, `tags` `["on_time", "friendly_driver"]`, `comment` `"Arrived on time and changed the flat safely"`, `moderation_status` `"pending"`, and numeric `driver_monthly_average` and `driver_monthly_count`

### RSA-006-AC2 [api]
- **Given** member Alice has a request in status `received`, `assigned`, `en_route`, `arrived`, or `cancelled` (or a `completed` request with no assigned driver)
- **When** Alice sends `POST /v1/requests/{id}/rating` with `stars` `5`
- **Then** the response is `409` with code `INVALID_TRANSITION`

### RSA-006-AC3 [api]
- **Given** member Alice has a `completed` request with an assigned driver and no rating yet
- **When** she sends `POST /v1/requests/{id}/rating` with `stars` `6`, an unknown tag `"super_fast"`, or a `comment` longer than `300` characters
- **Then** the response is `422` with code `VALIDATION_ERROR`, and `errors` names the invalid field (`stars`, `tags`, or `comment`)

### RSA-006-AC4 [api]
- **Given** member Alice has already submitted a rating for her `completed` request
- **When** she sends `POST /v1/requests/{id}/rating` again for the same request
- **Then** the response is `409` with code `ALREADY_RATED`

### RSA-006-AC5 [api]
- **Given** member Bob has a `completed` request
- **When** member Alice sends `POST /v1/requests/{id}/rating` for Bob's request
- **Then** the response is `404` with code `REQUEST_NOT_FOUND`

### RSA-006-AC6 [api]
- **Given** a signed-in dispatcher
- **When** they send `POST /v1/requests/{id}/rating` for a `completed` request
- **Then** the response is `403` with code `FORBIDDEN`

### RSA-006-AC7 [api]
- **Given** member Alice submits a rating with `stars` `5`, `tags` `["on_time"]`, and `comment` `"Call me at +1 555 010 9988 if needed"`
- **When** the audit log and recent structured logs are inspected
- **Then** the audit log has a `rating.created` event with `actor` `"alice"`, `target` equal to the request id, `stars` `5`, `tags` `["on_time"]`, and `has_comment` `true`, and no `http.request` or `audit` log line contains the comment text or `"010 9988"`

### RSA-006-AC8 [api]
- **Given** two drivers (including `"Marcus Rivera"`) have at least `1` rating in the current month, including one rating with a `pending` comment and one with an `approved` comment
- **When** an unauthenticated caller calls `GET /v1/leaderboard/drivers`, and when a signed-in member or dispatcher calls `GET /v1/leaderboard/drivers`
- **Then** the unauthenticated call returns `401` with code `UNAUTHENTICATED`, and the signed-in call returns `200` with `drivers` ordered by `average_stars` descending (tie-broken by `rating_count` descending, then `driver_display_name` ascending), each entry containing `rank`, `driver_display_name` (first name only, e.g. `"Marcus"` without `"Rivera"`), `driver_truck`, `average_stars`, `rating_count`, `tag_counts`, and `approved_comments` (containing only `approved` comments without member usernames, and excluding `driver_photo`, `pending` comments, and `rejected` comments)

### RSA-006-AC9 [api]
- **Given** a rating with a `pending` comment exists on request `{id}`
- **When** a signed-in dispatcher sends `PATCH /v1/requests/{id}/rating` with `{"moderation_status": "approved"}` (or `"rejected"`)
- **Then** the response is `200` with `moderation_status` `"approved"` (or `"rejected"`), the audit log has a `rating.moderated` event with `actor` `"dana"`, `target` `{id}`, and `moderation_status`, and `GET /v1/leaderboard/drivers` includes the comment only when `moderation_status` is `"approved"`

### RSA-006-AC10 [api]
- **Given** a rating with a `pending` comment exists on request `{id}`
- **When** a signed-in member sends `PATCH /v1/requests/{id}/rating` with `{"moderation_status": "approved"}`
- **Then** the response is `403` with code `FORBIDDEN`

### RSA-006-AC11 [ui]
- **Given** Alice is signed in and has one `en_route` request and one unrated `completed` request with an assigned driver
- **When** she opens the `en_route` request, then opens the `completed` request, selects `5` stars, toggles `"On time"` and `"Friendly driver"`, enters `"Smooth and safe tyre change"`, clicks **Submit rating**, and later reopens the rated request
- **Then** the `en_route` request page does not show `"How did we do?"`, the `completed` request page shows `"How did we do?"` with 5 stars, tags `"On time"`, `"Friendly driver"`, and `"Explained the fix"`, and a comment box, submitting displays `"Thank you for rating your rescue!"` with `"5 out of 5 stars"`, `"On time"`, `"Friendly driver"`, `"Smooth and safe tyre change"`, `"Pending moderation"`, the driver's updated monthly average, and no edit button, and reopening the rated request displays the submitted rating read-only with no `"How did we do?"` form

### RSA-006-AC12 [ui]
- **Given** a driver has a monthly rating with an approved comment and another rating with a pending comment
- **When** a signed-out visitor opens `/leaderboard`, and when signed-in member Alice opens `/leaderboard`
- **Then** the signed-out visitor is redirected to `/signin`, and Alice sees `"Top drivers this month"` with the driver's first name and truck, average stars, rating count, praise-tag counts, and the approved comment, while no driver photo, no driver last name, and no pending comment appear on the page

## Security & access (AAA)

### Authentication
Every `/v1` rating and leaderboard endpoint requires `Authorization: Bearer <token>` (AAA-1, AAA-2); missing or invalid tokens return `401` `UNAUTHENTICATED`. Both the rating view (`/requests/{id}`) and leaderboard page (`/leaderboard`) require sign-in; signed-out visitors are redirected to `/signin`.

### Authorization
| Action | Roles allowed |
|---|---|
| Submit a rating (`POST /v1/requests/{id}/rating`) | member (owner of `completed` request only; `404` for others per AAA-7; `403` for dispatcher per AAA-5) |
| View a request's rating (`GET /v1/requests/{id}`) | member (owner only; `404` for others per AAA-7), dispatcher |
| View monthly leaderboard (`GET /v1/leaderboard/drivers`) | member, dispatcher |
| Moderate a rating comment (`PATCH /v1/requests/{id}/rating`) | dispatcher (`403` for member per AAA-5) |

### Accounting
| Audit event | When | Details recorded |
|---|---|---|
| `rating.created` | A member submits a rating on a completed request | `actor`, `target` (request id), `driver`, `stars`, `tags`, `has_comment` (comment body omitted per LOG-4) |
| `rating.moderated` | A dispatcher approves or rejects a rating comment | `actor`, `target` (request id), `moderation_status` |

## Logging
Standard `http.request` line (LOG-2) and `event: "audit"` lines on rating creation and moderation (LOG-5), all carrying `request_id` (LOG-3). Member comments are free text that may include personal data (such as phone numbers or names) and are never logged in clear in `http.request` or `audit` events (LOG-4); `_scrub` continues to mask any phone-shaped value as defense in depth.

## API contract
| Method | Path | Success | Errors |
|---|---|---|---|
| POST | /v1/requests/{id}/rating | 201 | 401 UNAUTHENTICATED, 403 FORBIDDEN, 404 REQUEST_NOT_FOUND, 409 INVALID_TRANSITION, 409 ALREADY_RATED, 422 VALIDATION_ERROR |
| GET | /v1/requests/{id} | 200 (adds `rating` object or `null`) | 401 UNAUTHENTICATED, 404 REQUEST_NOT_FOUND |
| PATCH | /v1/requests/{id}/rating | 200 | 401 UNAUTHENTICATED, 403 FORBIDDEN, 404 REQUEST_NOT_FOUND, 404 RATING_NOT_FOUND, 409 INVALID_TRANSITION, 422 VALIDATION_ERROR |
| GET | /v1/leaderboard/drivers | 200 | 401 UNAUTHENTICATED, 422 VALIDATION_ERROR |

## SLO
```slo
p95_latency_ms: 300
error_rate_pct: 1.0
```

## Prototype reference
Link: `prototypes/rate-my-rescue/` (from branch `proto/rate-my-rescue`, screenshots in `prototypes/rate-my-rescue/screens/`)

| Screen / element | What the user sees or does | Data behind it | Became |
|---|---|---|---|
| Rescues list & status filters (`All`, `Completed`, `En route`) | Lists 5 sample rescues and lets user click any rescue — including `En route` ones — to rate it | `GET /v1/requests` (`id`, `type`, `location`, `status`, `driver`, `rating`) | `RSA-006-AC2`, `RSA-006-AC5`, `RSA-006-AC11` (en route rating blocked per #2; own requests only per AAA-7) |
| Rescue context banner (driver photo, full name, truck, status) | Displays driver headshot, full name, truck, help type, location, and status badge | Request fields (`driver_name`, `driver_truck`, `status`, `type`, `location`) | `RSA-006-AC8`, `RSA-006-AC11`, `RSA-006-AC12` (first name + truck only; photos and last names omitted) |
| En route notice ("still en route — submit a rating right now") | Lets members rate a truck while still en route | `status == "en_route"` | Rejected per #2 → `RSA-006-AC2` (`409 INVALID_TRANSITION`) and `RSA-006-AC11` (form hidden until `completed`) |
| "How did we do?" 5-star selector | Interactive 1–5 star rating with validation on submit | `stars` (`1..5`, required; validated per SEC-3) | `RSA-006-AC1`, `RSA-006-AC3`, `RSA-006-AC11` |
| Praise tags (`On time`, `Friendly driver`, `Explained the fix`) | Multi-select optional tags | `tags` enum (`on_time`, `friendly_driver`, `explained_fix`) | `RSA-006-AC1`, `RSA-006-AC3`, `RSA-006-AC11` |
| Comment box (optional, 300 chars) | Free-text note about the rescue | `comment` (string, max 300 chars; potential PII per LOG-4; moderated before display per #2) | `RSA-006-AC1`, `RSA-006-AC3`, `RSA-006-AC7`, `RSA-006-AC9`, `RSA-006-AC11` |
| Submit / Update rating button | Submits rating or edits an existing rating (`Update rating`) | `POST /v1/requests/{id}/rating` (`rating.created` audit per AAA-9) | `RSA-006-AC1`, `RSA-006-AC4`, `RSA-006-AC6`, `RSA-006-AC7` (editing removed per #2 → `409 ALREADY_RATED`) |
| Thank-you screen (`Thank you for rating your rescue!`) | Shows submitted stars, tags, comment, updated driver monthly average, link to leaderboard, and `Edit this rating` | `POST /v1/requests/{id}/rating` response | `RSA-006-AC11` (`Edit this rating` removed per #2; revisiting shows read-only rating) |
| Public leaderboard banner & `Copy public link` button | States "Public page · No sign-in required" and copies unauthenticated URL | `GET /v1/leaderboard/drivers`, `/leaderboard` | Rejected per #2 and AAA-1 → `RSA-006-AC8`, `RSA-006-AC12` (sign-in required) |
| "Top drivers this month" podium & standings (photos, full names, average stars, counts, tag filters, latest quote) | Ranked monthly drivers with portrait photos, full names, average stars, counts, tag counts/filters, and unmoderated member comments | Monthly aggregated ratings + approved comments only | `RSA-006-AC8`, `RSA-006-AC9`, `RSA-006-AC10`, `RSA-006-AC12` (first name + truck, no photos, minimum 1 rating, dispatcher moderation) |
| Prototype demo bar (`Reset demo data`) | Resets fake client-side demo state | Client-side only | Out of scope (prototype-only control) |

## Edge cases & errors
- Submitting a rating for a request in `received`, `assigned`, `en_route`, `arrived`, or `cancelled`: `409` `INVALID_TRANSITION`.
- Submitting a rating for a `completed` request with no assigned driver: `409` `INVALID_TRANSITION`.
- Submitting a second rating for an already-rated request: `409` `ALREADY_RATED`.
- Submitting a rating for an unknown request id or another member's request: `404` `REQUEST_NOT_FOUND` (AAA-7).
- `stars` missing, non-integer, `< 1`, or `> 5`: `422` `VALIDATION_ERROR` naming `stars`.
- Unknown value in `tags`: `422` `VALIDATION_ERROR` naming `tags` (duplicate valid tags are deduplicated in order).
- `comment` exceeding `300` characters: `422` `VALIDATION_ERROR` naming `comment`.
- Rating with empty/whitespace-only comment: stored as `comment: null` and `moderation_status: "none"`; attempting to moderate a rating with no comment returns `409` `INVALID_TRANSITION`.
- Moderating a request that has no rating yet: `404` `RATING_NOT_FOUND`.
- Leaderboard ranking: includes every driver with at least `1` rating in the requested month, ordered by `average_stars` descending, `rating_count` descending, `driver_display_name` ascending.
- Invalid `month` query parameter on `GET /v1/leaderboard/drivers` (must match `YYYY-MM`) or unknown `tag` filter: `422` `VALIDATION_ERROR`.

## Test data
- Seeded users: `alice` and `bob` (members), `dana` (dispatcher).
- Existing seeded request `RSA-1001` (Bob, `assigned`, driver `Sam`) remains unchanged for prior specs.
- Tests create and advance requests through `received` → `assigned` → `en_route` → `arrived` → `completed` (with an assigned driver) via the dispatcher `PATCH /v1/requests/{id}` endpoint to test rating creation, duplicate prevention, moderation, and leaderboard ranking independently.

## Open questions

### Resolved from issue #2
- [x] (Business) Should members only be able to rate completed rescues, or also rescues that are still en route? → Only `completed` rescues (#2).
- [x] (Business) Can a member change their rating after submitting it, or should each rescue only be rated once? → No changes after submitting; each completed rescue can only be rated once (#2).
- [x] (Business & Security — AAA-1) Should the "Top drivers this month" leaderboard be public without signing in, and are driver photos and full names OK to show publicly? → No; requires sign-in and must not expose driver photos or full names publicly (#2).
- [x] (Business) Should member comments appear on the leaderboard, and do they need moderation before being shown? → Yes; show comments on the leaderboard only after moderation (#2).

### Business
- [x] (Business) On the **signed-in** leaderboard and rating screen, how should drivers be displayed — first name + truck (e.g. `Sam · Truck 12`, no photos or last names), first name + last initial (e.g. `Marcus R.`), or something else? → First name + truck only (e.g. `Sam · Truck 12`), with no driver photos and no last names.
- [x] (Business) Should **dispatchers** (`dana`) be the role that moderates (approves/rejects) pending rating comments, with ratings/stars/tags counting immediately in the leaderboard while only `approved` comments are displayed? → Yes: dispatchers approve or reject pending comments; stars and tags count immediately while only `approved` comments appear on the leaderboard.
- [x] (Business) Should any driver with at least `1` rating this month appear on "Top drivers this month", or should there be a minimum number of ratings (e.g. `3`) before appearing? → Any driver with at least `1` rating this month appears immediately (ordered by `average_stars` desc, `rating_count` desc, `driver_display_name` asc).
- [x] (Business) If a request is marked `completed` with no driver assigned, should rating be rejected (`409`) or allowed without attributing to any driver on the leaderboard? → Reject with `409 INVALID_TRANSITION`.
- [x] (Business) When a member revisits an already-rated completed request on `/requests/{id}`, should they see their submitted rating read-only (stars, tags, comment, and moderation status) in place of the "How did we do?" form? → Yes: display the submitted rating read-only (with no edit button) in place of the rating form.

### IT / Security
- [x] (IT / Security — AAA-1, AAA-5) Confirm both `member` and `dispatcher` roles may view `GET /v1/leaderboard/drivers` and `/leaderboard`, while signed-out callers get `401 UNAUTHENTICATED` (API) / redirect to `/signin` (UI). → Confirmed.
- [x] (IT / Security — AAA-7) Confirm that a member sending `POST /v1/requests/{id}/rating` for another member's request gets `404 REQUEST_NOT_FOUND` (never `403`). → Confirmed.
- [x] (IT / Security — AAA-9, AAA-11) Confirm the two audit events: `rating.created` (actor: member, target: request id, details: `driver`, `stars`, `tags`, `has_comment`) and `rating.moderated` (actor: dispatcher, target: request id, details: `moderation_status`). → Confirmed.
- [x] (IT / Security — LOG-4) Confirm free-text `comment` content is never logged in clear in `http.request` or `audit` log entries (only `has_comment: true/false` in the audit event), and member usernames are omitted from `approved_comments` on the leaderboard. → Confirmed.
- [x] (IT / Security — SLO-1) Confirm the default SLO (`p95_latency_ms: 300`, `error_rate_pct: 1.0`) applies to rating creation, moderation, and the monthly leaderboard. → Confirmed.
