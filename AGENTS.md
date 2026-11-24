# AGENTS.md

Antigravity, Claude Code, Gemini CLI and other agents read this file first. It says what this
app is and where the rules are. It holds no rules of its own: **every rule lives in
`standards/`** (the SDLC Standards repository, pinned to a version), and has an ID such as
AAA-7 or SEC-4. Quote the IDs in specs, plans and pull requests where they decide something.

If `standards/` is empty, run `git submodule update --init` first.

**The app:** Roadside Assistance, a demo member and dispatcher portal for AAA. Members ask
for help (tow, battery, flat tyre, lockout, fuel); dispatchers move each request along.

## The cycle

```
feature request (GitHub issue), optionally linking a prototype
  → spec (approved by a person)                          /write-spec #<issue>
  → tests → code → standards/checks/all.sh → local run
  → GKE dev sandbox: ALL tests → evidence → pull request  /build-spec specs/<file>
  → CI repeats every check in a PR sandbox → a person reviews and merges
  → UAT on Cloud Run → release: canary judged by the SLO  /release #<PR>
      → promote, or roll back + SRE agent's root-cause PR  /sre-review
```

## Where the rules are

| When you are… | Read |
|---|---|
| Writing a feature request or a spec, or reading a prototype | `standards/spec.md`, `standards/templates/spec.md` |
| Deciding sign-in, roles or audit events | `standards/aaa.md` |
| Designing endpoints and errors | `standards/api.md` |
| Logging anything | `standards/logging.md` |
| Writing code or adding a library | `standards/coding.md` (approved libraries at the end) |
| Touching input, HTML, cookies, containers, secrets or CI | `standards/security.md` |
| Writing tests | `standards/testing.md` |
| Committing, opening a PR, deploying | `standards/delivery.md` |
| Releasing, or explaining a canary | `standards/release.md` |

Before every commit: `standards/checks/all.sh` must pass (DEL-3).

## Never
- Commit to `main`, approve, force-push, or delete branches you didn't create (DEL-2).
- Change a criterion or weaken a test to make something pass (TEST-8).
- Take a business decision the issue doesn't contain: ask, or list it as an open question (SPEC-10).
- Post an issue, comment or PR before showing the person its text (DEL-5).
- Open a PR without a green dev-sandbox run for the exact commit (DEL-3).
- Edit anything under `standards/`. Standards change only in the SDLC Standards repository (SEC-12).

## This app's specifics

These are facts about this repository, not rules.

- **Spec IDs:** `RSA-` for features, `STD-` for the shared baseline (`specs/STD-001`, which
  tests the standards on every run).
- **API** (`services/api`): FastAPI, in-memory storage seeded at start (`SEED_TEST_DATA=true`):
  users `alice`, `bob` (members), `dana` (dispatcher); request `RSA-1001` (Bob's). Use
  `require("member", ...)` for roles, `audit(...)` for every change, `ApiError(status, code,
  message)` for errors. Logging and request IDs are automatic. Test-only endpoints are
  registered only `if TEST_HOOKS:`.
- **Partner system:** the Driver Directory, through `services/api/driver_directory.py`
  (`lookup(driver_name)`). Each call is a round trip to the partner; test environments use an
  instant stub.
- **Website** (`services/web`): FastAPI-rendered pages. The browser only talks to the website,
  which calls the API server-side with the signed-in user's token (cookie `session`).
- **API test fixtures** (`tests/api/conftest.py`): `api` (signed out), `as_user("alice")`,
  `token("dana")`, `new_request()`.
- **UI test helpers** (`tests/ui/helpers.ts`): `signIn(page, 'alice')`; `API`, `apiToken()` and
  `apiHeaders()` to set up data through the API.
- **Environments:** dev sandbox `dev-<repo>-<branch>`, PR sandbox `<repo>-pr-<N>` (GKE);
  UAT `tp-sdlc-uat-web` / `-api` (Cloud Run); production `<repo>-prod` (GKE, 9 stable + 1 canary).

## Commands

| Command | What it does |
|---|---|
| `standards/checks/all.sh` | Every standards check that runs without the cloud |
| `gh issue create --title "[Request] …" --label request --body-file .tmp/feature-request.md` | Post a feature request (SPEC-1), after showing it |
| `cd services/api && ENABLE_TEST_HOOKS=true uvicorn app:app --port 8080` | Run the API locally |
| `cd services/web && API_URL=http://localhost:8080 uvicorn app:app --port 3000` | Run the website locally |
| `API_BASE_URL=http://localhost:8080 pytest tests/api -q` | API tests |
| `cd tests/ui && WEB_BASE_URL=http://localhost:3000 API_BASE_URL=http://localhost:8080 npx playwright test` | UI tests |
| `scripts/sandbox.sh all` / `publish` / `load` / `down` | Dev sandbox on GKE: run all tests, post evidence, load test, delete |
| `scripts/prod.sh status` | What runs in production. Never `promote` or `canary` yourself (REL-6) |
