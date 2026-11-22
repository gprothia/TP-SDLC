---
id: XXX-000            # area prefix + number, e.g. RSA-004
title: Short feature name
status: draft          # draft | approved | implemented
owner: "@github-handle"
issue: "#123"          # the feature request (or prototype) this came from
---

# XXX-000: Short feature name

## Why
One or two sentences: the user problem and the outcome.

## Scope
- In: ...
- Out: ...

## Acceptance criteria
<!--
One block per criterion: ### <ID>-AC<n> [api] | [ui] | [api,ui]. Never renumber.
Given / When / Then, with exact status codes, error codes, field names and visible text.
Include the control criteria the enterprise sections below imply (401, 403, audit event).
-->

### XXX-000-AC1 [api]
- **Given** ...
- **When** ...
- **Then** ...

## Security & access (AAA)
<!-- standards/aaa.md -->

### Authentication
Who must be signed in, and what happens otherwise.

### Authorization
| Action | Roles allowed |
|---|---|
| ... | member |

### Accounting
| Audit event | When | Details recorded |
|---|---|---|
| `thing.created` | ... | ... |

## Logging
<!-- standards/logging.md: what this feature logs; any personal data and how it's masked -->

## API contract
<!-- standards/api.md -->
| Method | Path | Success | Errors |
|---|---|---|---|
| GET | /v1/... | 200 | 401, 403, 404 |

## SLO
<!-- standards/slo.md: governs the production canary -->
```slo
p95_latency_ms: 300
error_rate_pct: 1.0
```

## Prototype reference
<!-- Only when the request linked a prototype; delete otherwise.
Link: prototypes/<name>/ (from branch proto/<name>)
| Screen / element | What the user sees or does | Data behind it | Became |
|---|---|---|---|
| ... | ... | ... | XXX-000-AC1, or open question |
-->

## Edge cases & errors
- ...

## Test data
Seeded users and records the tests may rely on.

## Open questions
- [ ] ...
