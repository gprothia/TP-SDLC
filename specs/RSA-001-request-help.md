---
id: RSA-001
title: Request roadside help
status: implemented
owner: "@gprothia"
issue: "#2"
---

# RSA-001: Request roadside help

## Why
Members stranded on the road need to ask for help in seconds, without calling.

## Scope
- In: a signed-in member sends a request (type of help, location, phone) and sees it was received.
- Out: payment, membership checks, GPS location.

## Acceptance criteria

### RSA-001-AC1 [api]
- **Given** a signed-in member
- **When** they send `POST /v1/requests` with type `tow`, a location and phone `+1 555 010 1234`
- **Then** the response is `201` with an `id` starting `RSA-`, `status` `received`, and `member` equal to their user

### RSA-001-AC2 [api]
- **Given** a signed-in member
- **When** they send type `boat`
- **Then** the response is `422` with code `VALIDATION_ERROR`, and its `errors` list names field `type`

### RSA-001-AC3 [api]
- **Given** a signed-in member
- **When** they send phone `12345`
- **Then** the response is `422`, and its `errors` list names field `phone`

### RSA-001-AC4 [api]
- **Given** a signed-in dispatcher
- **When** they send `POST /v1/requests`
- **Then** the response is `403` with code `FORBIDDEN`

### RSA-001-AC5 [api]
- **Given** a member creates a request
- **Then** the audit log has a `request.created` event with that member as actor and the request id as target

### RSA-001-AC6 [ui]
- **Given** Alice is signed in
- **When** she chooses "Battery jump-start", enters a location and phone, and clicks **Send request**
- **Then** she sees "Help is on the way" and the status "Received"

## Security & access (AAA)

### Authentication
Members must be signed in. Signed-out visitors are sent to `/signin`.

### Authorization
| Action | Roles allowed |
|---|---|
| Create a request | member |

### Accounting
| Audit event | When | Details recorded |
|---|---|---|
| `request.created` | A member sends a request | actor, target (request id), type |

## Logging
Standard `http.request` line. The phone number is personal data: never logged in clear.

## API contract
| Method | Path | Success | Errors |
|---|---|---|---|
| POST | /v1/requests | 201 | 401, 403, 422 |

## SLO
```slo
p95_latency_ms: 300
error_rate_pct: 1.0
```

## Edge cases & errors
- Location under 3 characters: `422` for field `location`.

## Test data
Help types: `tow`, `battery`, `flat_tyre`, `lockout`, `fuel`.

## Open questions
- [x] Can dispatchers create requests on a caller's behalf? → Not in this feature.
