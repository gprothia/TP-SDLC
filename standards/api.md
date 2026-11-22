# API design

- API-1. Paths are versioned and plural: `/v1/requests`, `/v1/requests/{id}`.
- API-2. Errors always have the body `{"code": "UPPER_SNAKE", "message": "...", "request_id": "..."}`.
  Validation errors add `errors: [{"field": "phone", "message": "..."}]` and use `422`.
- API-3. Status codes: `200` read/update, `201` create, `401` not signed in, `403` wrong role,
  `404` not found (or not yours), `409` conflicting state, `422` invalid input.
- API-4. Every response carries `X-Request-ID`. A caller's own `X-Request-ID` is kept.
- API-5. Updates are partial (`PATCH`); state machines reject skipped steps with `409`.
- API-6. Each spec lists its endpoints in an **API contract** section.
