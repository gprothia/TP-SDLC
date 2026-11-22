# Logging

- LOG-1. One JSON object per line on stdout (Cloud Logging reads it as structured logs).
- LOG-2. Every request writes one `http.request` line: `ts`, `severity`, `request_id`,
  `method`, `path`, `status`, `duration_ms`, `user`, `role`.
- LOG-3. Every line carries the request's `request_id`, so one request can be traced end to end.
- LOG-4. Never log personal data in clear. Phone numbers are masked to the last two digits
  (`********33`). Request bodies are not logged.
- LOG-5. Audit events are logged with `event: "audit"` (see `aaa.md`, AAA-10).
- LOG-6. Each spec says what its feature logs in a **Logging** section.
