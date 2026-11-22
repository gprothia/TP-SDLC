# TP-SDLC: Roadside Assistance, built the spec-driven way

A demo for AAA showing three things in one storyline:

1. **Specs and issues become executable API and UI test suites**, run in ephemeral GKE
   Autopilot sandboxes before and on every PR. *(working)*
2. **Business vibe-codes a UI prototype; an Antigravity agent reverse-engineers it into a
   hardened enterprise spec** (AAA sign-in, roles and audit; logging; API standards; SLO) that IT
   agents build. *(phase 2)*
3. **SLO-governed canary releases on GKE replace change-board sign-offs** for standard
   changes; an SRE agent rolls back a bad canary and opens a root-cause PR. *(phase 3)*

The app is a small **Roadside Assistance portal**: members ask for help (tow, battery, flat
tyre, lockout, fuel); dispatchers move each request along. *Demo application, not an AAA product.*

## What's where

| Path | Purpose |
|---|---|
| `AGENTS.md` | The one rulebook every agent follows |
| `standards/` | **Enterprise standards**: AAA, API, logging, SLO, code style, security |
| `specs/` | What the app must do. `_TEMPLATE.md` includes the required enterprise sections |
| `services/api`, `services/web` | The API (FastAPI, `/v1`) and the website (sign-in, requests, dispatcher updates) |
| `tests/api`, `tests/ui` | pytest and Playwright suites; every test tagged with its spec rule |
| `scripts/check_spec.py` | Rejects specs missing a section, a permissions table, audit events or an SLO |
| `scripts/check_traceability.py` | Every approved rule has a test |
| `scripts/sandbox.sh` | Pre-PR GKE run: build, stage as pods, run all tests, publish evidence |
| `ruff.toml`, `tests/ui/eslint.config.mjs` | Code style and safety rules the tools enforce |
| `.agents/workflows/` | Antigravity commands: `/write-spec`, `/build-spec` |
| `.github/workflows/` | PR checks (spec, coverage, style, Gemini, GKE), UAT deploy, cleanup |
| `.github/CODEOWNERS` | Who must approve changes to standards and deployment |

## The app today

| Spec | Feature | Rules | Tests |
|---|---|---|---|
| `STD-001` | Enterprise baseline: sign-in on every endpoint, error format, request IDs, structured masked logs, sign-in audit | 8 | 13 API, 1 UI |
| `RSA-001` | Request roadside help | 6 | 5 API, 1 UI |
| `RSA-002` | View requests: members their own, dispatchers all | 5 | 3 API, 2 UI |
| `RSA-003` | Dispatcher updates status, ETA, driver | 5 | 4 API, 1 UI |

Demo users (sign-in page): **Alice** and **Bob** (members), **Dana** (dispatcher).
Sign-in is simulated (`standards/aaa.md` AAA-3); in production the company identity provider
issues the same kind of token.

## Run it locally

```bash
pip install -r services/web/requirements.txt -r tests/requirements.txt
(cd services/api && ENABLE_TEST_HOOKS=true uvicorn app:app --port 8080 &)
(cd services/web && API_URL=http://localhost:8080 uvicorn app:app --port 3000 &)
open http://localhost:3000

API_BASE_URL=http://localhost:8080 pytest tests/api -q
cd tests/ui && npm ci && npx playwright install chromium \
  && WEB_BASE_URL=http://localhost:3000 API_BASE_URL=http://localhost:8080 npx playwright test
```

## A feature cycle in Antigravity

1. **Request**: GitHub → Issues → New issue → *Feature request* (plain words).
2. **Spec**: `/write-spec #<issue>`: drafts `specs/RSA-00N-...md` with every enterprise
   section, runs the checker, asks the open questions. You approve.
3. **Build**: `/build-spec specs/<file>`: plan → failing tests → code → style checks →
   GKE sandbox with the full regression → PR with evidence.
4. **Merge**: CI re-checks; merging deploys to UAT on Cloud Run with smoke tests and rollback.

## Google Cloud and GitHub setup

Reuses project `bold-kit-384717` (`us-central1`), cluster `pr-sandboxes` and registry
`pr-sandbox` (`deploy/sandbox/sandbox.env`). TP-SDLC needs its own trust rule
and UAT identities. In Cloud Shell:

```bash
PROJECT_ID=bold-kit-384717; GH_REPO=gprothia/TP-SDLC
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
SA=gh-pr-sandbox@$PROJECT_ID.iam.gserviceaccount.com

gcloud iam workload-identity-pools providers create-oidc github-tp-sdlc \
  --location=global --workload-identity-pool=github --project $PROJECT_ID \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='$GH_REPO'"
gcloud iam service-accounts add-iam-policy-binding $SA --project $PROJECT_ID \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github/attribute.repository/$GH_REPO"
```

The UAT identities (`uat-api`, `uat-web`) and pipeline rights are shared with the earlier demo repositories. UAT runs as its own Cloud Run services, `tp-sdlc-uat-api` and `tp-sdlc-uat-web`.

**Repository variables** (Settings → Secrets and variables → Actions → Variables):

| Variable | Value |
|---|---|
| `GCP_PROJECT_ID` | `bold-kit-384717` |
| `GCP_REGION` | `us-central1` |
| `GKE_CLUSTER` | `pr-sandboxes` |
| `AR_REPO` | `pr-sandbox` |
| `WIF_PROVIDER` | `projects/851970768145/locations/global/workloadIdentityPools/github/providers/github-tp-sdlc` |
| `CI_SERVICE_ACCOUNT` | `gh-pr-sandbox@bold-kit-384717.iam.gserviceaccount.com` |

Until they're set, CI runs only the spec, coverage and style checks.

## Known limits (demo)
- Sign-in is simulated with demo tokens; storage is in memory and resets on restart.
