# AAA: Authentication, Authorization, Accounting

## Authentication: who are you?
- AAA-1. Every `/v1` endpoint requires `Authorization: Bearer <token>`, except sign-in.
  Missing or invalid token: `401` with code `UNAUTHENTICATED`.
- AAA-2. Tokens expire (8 hours here). An expired token is treated as missing.
- AAA-3. Demo only: `POST /v1/auth/demo-login` issues a token for a seeded user. In
  production the company identity provider (SSO) issues it; nothing else changes.
- AAA-4. On Cloud Run the API is also private at the platform level: only the website's and
  the pipeline's service accounts may reach it (`X-Serverless-Authorization`).

## Authorization: what may you do?
- AAA-5. Deny by default. Each endpoint lists the roles allowed; any other role gets `403`
  with code `FORBIDDEN`.
- AAA-6. Roles: `member` (a customer) and `dispatcher` (staff).
- AAA-7. Never reveal that someone else's record exists: a member asking for another
  member's record gets `404`, not `403`.
- AAA-8. Every spec has an **Authorization** table: action → roles.

## Accounting: what did you do?
- AAA-9. Every sign-in and every change writes an audit event: `event`, `actor`, `target`,
  `at`, `request_id`, and what changed.
- AAA-10. Audit events are also written to the log (`event: "audit"`), so they reach the
  central log store. Dispatchers can read them at `GET /v1/audit`.
- AAA-11. Event names are `<thing>.<past-tense verb>`: `request.created`, `request.updated`.
