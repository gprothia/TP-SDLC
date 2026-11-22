# Service levels and releases

## Every feature has an SLO
- SLO-1. Each spec has an **SLO** section with a machine-readable block:

  ```slo
  p95_latency_ms: 300
  error_rate_pct: 1.0
  ```

  `p95_latency_ms`: 95% of requests finish within this time. `error_rate_pct`: share of
  requests that may fail with a `5xx`. Defaults if a feature has no special need: 300 ms, 1%.

## Releases replace the change board for standard changes
- SLO-2. A **standard change** is a merged PR whose specs pass `check_spec.py`, whose tests
  passed in its GKE sandbox (check "Spec acceptance tests"), which has no `needs-approval`
  label, and which touches none of: `standards/`, `deploy/prod/`, `.github/CODEOWNERS`, or
  the release gate itself (`.github/workflows/release.yml`, `scripts/classify_change.py`,
  `scripts/check_slo.py`, `scripts/prod.sh`, `tools/loadgen.py`). Checked by
  `scripts/classify_change.py`; the same PR always gets the same answer.
- SLO-3. Standard changes go to production as a **canary**: about 10% of traffic for a
  fixed window, measured against the strictest SLO of the specs it touches (the defaults
  above if it touches none). Fewer than 100 canary requests is no evidence, so no release.
  In this demo the traffic is synthetic (`tools/loadgen.py`) and production is the
  `<repo>-prod` namespace on the shared GKE cluster.
- SLO-4. Within budget: promoted to 100% automatically. Over budget: rolled back
  automatically, and the SRE agent opens a root-cause PR. No meeting is needed either way;
  the evidence is in GitHub.
- SLO-5. Anything that is not a standard change still needs a human approval before release:
  a reviewer of the GitHub `production` environment approves the release run. The canary
  and its SLO check still apply after approval.
