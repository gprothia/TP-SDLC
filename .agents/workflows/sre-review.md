---
description: Review the SRE agent's root-cause PR after a rollback - explain it, load-test the fix on GKE, post the evidence (rules in AGENTS.md section 6)
---

# /sre-review

Usage: `/sre-review` (latest open PR labelled `sre-agent`) or `/sre-review #<PR>`.

## 1. Understand
// turbo
1. `gh pr list --label sre-agent --state open -L 1` (unless a number was given), then
   `gh pr view <PR>` and `gh pr diff <PR>`.
2. Explain to the user, in plain words: what broke (endpoint, numbers vs budget), the root
   cause (file, function, mechanism), why tests didn't catch it, and what the fix changes.
   Check the fix yourself: does it remove the cause? Does it keep the API response the
   same? Does it break any standard (logging, AAA, code style)? Say what you think.
3. If the fix is wrong or incomplete, propose the change and ask before committing it.

## 2. Prove the fix under production-like load
// turbo
4. `git fetch origin && git switch <PR branch>` (`gh pr view <PR> --json headRefName -q .headRefName`).
// turbo
5. `scripts/sandbox.sh all`: all tests on GKE in `dev-<repo>-<branch>`. Must be green.
// turbo
6. `scripts/sandbox.sh load`: the same app with the partner's production latency and
   synthetic member traffic, judged against the SLO. Show the table. Must be PASSED.
7. Show the user what you will post, then `scripts/sandbox.sh publish`: the commit status
   and one PR comment with the test results and the load test.

## 3. Hand over
8. Summarise: root cause, fix, "all tests green on GKE", "load test p95 <x> ms ≤ <budget> ms".
   The PR's own checks run too. A person reviews and merges; `/release #<PR>` then ships it
   through the canary again. Leave the sandbox running for the demo; the user runs
   `scripts/sandbox.sh down` when done.
