# Security basics

- SEC-1. No secrets in the repo. Real secrets live in Secret Manager. (The demo sign-in key is
  deliberately not a secret and only signs demo tokens.)
- SEC-2. Test-only endpoints live under `/test/...`, exist only when `ENABLE_TEST_HOOKS=true`
  (off by default), and are never on in UAT or production.
- SEC-3. Input is validated at the API edge; invalid input gets `422` with the field named.
- SEC-4. Dependencies are pinned to exact versions.
- SEC-5. Changes to `standards/` need the owning team's approval (`.github/CODEOWNERS`).
