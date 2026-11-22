---
description: Show what is running in production on GKE (stable vs canary) and the latest release verdict
---

# /canary-status

Read-only. Explain in plain words.

// turbo
1. `scripts/prod.sh status`: copies per track (stable / canary) and version, and the pods.
   Say how many copies run which commit, e.g. "9 stable copies of 1a2b3c4, no canary".
// turbo
2. `gh run list --workflow release.yml -L 3`: the latest releases and their outcome.
3. For the latest one, find the merged PR (`gh api repos/{owner}/{repo}/commits/<sha>/pulls --jq '.[0].number'`)
   and show its release record comment: the SLO table and verdict.
4. If a canary copy is running and no release run is in progress, say so: it is left over;
   suggest `scripts/prod.sh rollback`, but don't run it unless the user asks.
