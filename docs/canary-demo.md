# Demo: canary releases instead of a change board

**Story:** routine changes go to production on evidence, not a meeting. The spec's SLO is the
contract; a canary on GKE checks it with traffic; the pipeline promotes or rolls back; after a
rollback an SRE agent hands you the root cause and a fix. Risky changes still need a named
approver.

Rules: `standards/release.md`. Pipeline: `.github/workflows/release.yml`. Antigravity commands:
`/release`, `/canary-status`, `/sre-review`.

## One-time setup

1. **Settings → Actions → General → Workflow permissions** → tick *Allow GitHub Actions to
   create and approve pull requests* (the SRE agent opens its PR).
2. **Settings → Environments → New environment** `production` → **Required reviewers**: you.
   Non-standard changes wait for your click (REL-5). Without it they fail with a clear message.

## Before the client arrives (about 15 min)

- Production space up: `scripts/prod.sh status` (create it with `scripts/prod.sh up`).
- The demo change is ready and green: PR **"RSA-005: verified driver badge"** (base `main`).
- Tabs: Antigravity; GitHub **Actions**; Cloud Console **Kubernetes Engine → Workloads**
  filtered to namespace `tp-sdlc-prod`; `specs/RSA-005-verified-driver.md` at its **SLO**.
- Optional: rehearse once, so GKE capacity is warm.

## Scene 1: a "harmless" change is caught (about 10 min)

| Do (Antigravity) | Show / say |
|---|---|
| Open the RSA-005 spec, **SLO**: 300 ms, 1% | "Every spec carries a performance promise. That's the release contract." |
| `/release #<RSA-005 PR>` | The agent checks the PR is green and predicts *standard change*. Say yes to merge. |
| (UAT runs, about 5 min) | "UAT first: Cloud Run, smoke tests. Nobody presses anything after the merge." |
| Classification | ✅ reasons: "Routine by our rules, so no meeting: it goes to canary." |
| Canary running | Workloads: **9 `api-stable` + 1 `api-canary`**. "1 in 10 requests hit the new version." |
| Verdict | **p95 about 600 ms > 300 ms ❌ → rolled back.** `/canary-status`: 9 stable, no canary. "Undone in minutes; 90% of users never saw it." |

## Scene 2: the SRE agent explains and fixes (about 8 min)

| Do | Show / say |
|---|---|
| GitHub **Pull requests**: *"Rollback of …: Request details p95 …"* (labels `incident`, `sre-agent`) | "Opened by the SRE agent, Gemini, without anyone asking." |
| Open it: incident report and diff | Root cause: *partner lookup on every request*, file and function, why tests missed it (test stub is instant), the fix: a cache. |
| `/sre-review` | The agent explains it, runs all tests on GKE, then a **load test with production latency**: *p95 about 30 ms ✅*, and posts the evidence on the PR. |

## Scene 3: the fix ships itself (about 8 min)

| Do | Show / say |
|---|---|
| `/release #<root-cause PR>` | Standard change → canary → **p95 well under 300 ms ✅ → promoted**. "Same rules, no meeting, and now the feature is live." |
| Merged PR: **release record** comment | "Who, what, numbers, verdict: that's the audit trail a CAB form used to give you." |

## Scene 4 (optional): risky changes still need a person (about 3 min)

Move TP-SDLC to a new version of the SDLC standards in its own PR (the `standards` submodule),
merge it, then `/release`.
The release run shows ⏸ **Waiting for review**. Open the run → **Review deployments → Approve**.
"A new version of the rules gets a named approver, recorded in GitHub. The canary still checks it."

## Afterwards

- `scripts/prod.sh down` removes the production space (10 small pods).
- `scripts/sandbox.sh down` on the branch `/sre-review` used.
- To show it again: re-run the scenes with a new change, or use **Actions → Release (canary)
  → Run workflow** to re-release the current `main`.

## If something goes wrong live

- Keep the finished rehearsal runs open in tabs (one rollback, one promote) and walk through those.
- A stuck canary: `scripts/prod.sh rollback`.
- Shorter measurement: **Run workflow** with `duration` 90 (the default is 180 s).
