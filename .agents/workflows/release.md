---
description: Merge a green PR and follow its release - UAT, standard-change check, GKE canary, SLO verdict, promote or rollback (rules: standards/release.md)
---

# /release

Usage: `/release #<PR>`. Rules: `standards/release.md` (REL-2 to REL-6). Explain each stage to the user in
plain words as it happens; they may be presenting this to a client.

## 1. Ready to merge?
// turbo
1. `gh pr view <PR> --json number,title,state,mergeable,headRefOid,labels,files` and
   `gh pr checks <PR>`. Summarise: title, files changed, checks (all must be green).
   If anything is red or pending, stop and say what.
2. Predict the release path with the same rule the pipeline uses (REL-2):
   list the changed files, and say "standard change: canary, no approval" or "not standard
   because <gated files / label>: a reviewer must approve in GitHub".
3. Ask the user: "Merge PR #<n> now?" Wait for a clear yes. Then
   `gh pr merge <PR> --merge` and note the merge commit: `gh pr view <PR> --json mergeCommit -q .mergeCommit.oid`.

## 2. UAT (Cloud Run)
// turbo
4. Find the run: `gh run list --workflow deploy-uat.yml --commit <merge sha> --json databaseId,status -L 1`
   (retry every 10 s until it appears), then `gh run watch <id> --exit-status`.
   Say: "UAT is building this commit, deploying to Cloud Run and smoke-testing it."
   If it fails, stop: UAT rolled itself back and there is no canary.

## 3. Release (canary)
// turbo
5. Find the run: `gh run list --workflow release.yml --commit <merge sha> --json databaseId,status,url -L 1`
   (retry until it appears). Print its URL.
6. Classification: `gh run view <id> --log --job <classify job id>` (job ids: `gh run view <id> --json jobs`).
   Show the ✅/❌ reasons. If it is waiting for approval, tell the user to open the run and
   click **Review deployments → Approve** in GitHub. Never approve it yourself.
7. While the canary job runs, every ~60 s run `scripts/prod.sh status` and say what changed:
   "1 canary copy of <sha> is serving next to 9 stable copies (about 10% of traffic)",
   "measuring with synthetic member traffic for <n> s".
8. When the run finishes: `gh run view <id>` and read the release record comment on the PR
   (`gh pr view <PR> --comments`, the one starting `### ✅ Released` or `### ❌ Rolled back`).
   Show the SLO table: budget, stable, canary, verdict.

## 4. Result
9. Promoted: "Released by SLO evidence; no change-board meeting. All copies now run <sha>."
   Run `scripts/prod.sh status` to show it.
10. Rolled back: "The canary broke its budget and was removed; users are on the previous
    version." Wait for the `sre-agent` job, then print the root-cause PR
    (`gh pr list --label sre-agent --state open -L 1`) and suggest `/sre-review`.
