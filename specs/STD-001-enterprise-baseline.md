---
id: STD-001
title: Enterprise baseline (AAA, logging, API, web security)
status: implemented
owner: "@gprothia"
issue: "#1"
---

# STD-001: Enterprise baseline (AAA, logging, API, web security)

## Why
The standards in `standards/` (SDLCStandards) apply to every endpoint. This spec turns the shared ones into
tests, so every PR proves them again, not just the features it changes.

## Scope
- In: authentication on every `/v1` endpoint, error format, request IDs, structured and
  masked logs, sign-in audit, sign-in required on every page, security headers and the
  session cookie's flags (SEC-8, SEC-9).
- Out: feature-specific roles and audit events (each feature spec covers its own).

## Acceptance criteria

### STD-001-AC1 [api]
- **Given** no `Authorization` header
- **When** any `/v1` endpoint other than `POST /v1/auth/demo-login` is called
- **Then** the response is `401` with code `UNAUTHENTICATED`

### STD-001-AC2 [api]
- **Given** a token whose signature has been altered
- **When** `GET /v1/requests` is called with it
- **Then** the response is `401` with code `UNAUTHENTICATED`

### STD-001-AC3 [api]
- **Given** a request carrying `X-Request-ID: std-check-123`
- **When** any endpoint answers
- **Then** the response carries `X-Request-ID: std-check-123`; without one, a new ID is returned

### STD-001-AC4 [api]
- **Given** any error response
- **Then** its body has `code`, `message` and `request_id`, and `request_id` equals the `X-Request-ID` header

### STD-001-AC5 [api]
- **Given** a signed-in member creates a request
- **When** the recent logs are read
- **Then** there is an `http.request` line with that `request_id`, `method`, `path`, `status`, `duration_ms`, `user` and `role`

### STD-001-AC6 [api]
- **Given** a request created with phone `+1 555 010 4477`
- **When** the recent logs are read
- **Then** no line contains `010 4477` or `0104477`

### STD-001-AC7 [api]
- **Given** a user signs in as `alice`
- **Then** the audit log has an `auth.signed_in` event with actor `alice`

### STD-001-AC8 [ui]
- **Given** a visitor who is not signed in
- **When** they open `/requests`
- **Then** they are sent to `/signin`, which shows a "Sign in as Alice Ng (member)" button

### STD-001-AC9 [ui]
- **Given** any visitor
- **When** they open `/signin`
- **Then** the response carries `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: same-origin`, `Content-Security-Policy: frame-ancestors 'none'` and
  `Strict-Transport-Security: max-age=31536000` (SEC-8)

### STD-001-AC10 [ui]
- **Given** a user signs in as `alice`
- **Then** the browser holds a `session` cookie that is `HttpOnly` and `SameSite=Lax`, and also
  `Secure` when the website is served over `https` (SEC-9)

### STD-001-AC11 [api]
- **Given** any `/v1` request, signed in or not
- **Then** the response carries `X-Content-Type-Options: nosniff` and `Cache-Control: no-store` (SEC-8)

## Security & access (AAA)

### Authentication
All `/v1` endpoints except sign-in require a bearer token (AAA-1, AAA-2). The website keeps
the token in an `HttpOnly`, `SameSite=Lax`, `Secure` cookie (SEC-9).

### Authorization
| Action | Roles allowed |
|---|---|
| Sign in (demo) | anyone |
| Read own profile `/v1/me` | member, dispatcher |
| Read the audit log | dispatcher |

### Accounting
| Audit event | When | Details recorded |
|---|---|---|
| `auth.signed_in` | A user signs in | actor, target (the user) |

## Logging
One `http.request` line per request (LOG-2); phone numbers masked
(LOG-4); audit events logged (LOG-5).

## API contract
| Method | Path | Success | Errors |
|---|---|---|---|
| POST | /v1/auth/demo-login | 200 | 404 USER_NOT_FOUND, 422 |
| GET | /v1/me | 200 | 401 |
| GET | /v1/audit | 200 | 401, 403 |

## SLO
```slo
p95_latency_ms: 300
error_rate_pct: 1.0
```

## Edge cases & errors
- Expired token: same as a missing token (`401`).

## Test data
Seeded users: `alice` and `bob` (members), `dana` (dispatcher).

## Open questions
- [x] Which identity provider in production? → Out of scope for the demo; demo sign-in stands in.
