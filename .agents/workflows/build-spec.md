---
description: Build an approved spec - tests, code, GKE staging with full regression, evidence, PR (rules in AGENTS.md)
---

# /build-spec

Usage: `/build-spec specs/<ID>-<name>.md`. Follow `AGENTS.md` sections 3–5.

## 1. Check and plan
// turbo
1. `python scripts/check_spec.py <spec>` passes and the spec is `status: approved`; you are on
   its `feat/...` branch. Otherwise stop: the spec needs `/write-spec` first.
2. Plan: for each acceptance criterion, the tests to add (file + name) and the code changes.
   Note anything ambiguous. **Wait for the user to approve the plan.**

## 2. Tests first
3. Write the tests (`AGENTS.md` section 3).
// turbo
4. `python scripts/check_traceability.py` passes.
5. Run the app and both suites locally. The new tests fail (nothing built yet); all old tests
   pass. Show the user the failing list - it is the definition of done.
   - `ruff format . && ruff check .` and `cd tests/ui && npx eslint .` (style, standards/code-style.md)
   - `cd services/api && ENABLE_TEST_HOOKS=true uvicorn app:app --port 8080`
   - `cd services/web && API_URL=http://localhost:8080 uvicorn app:app --port 3000`
   - `API_BASE_URL=http://localhost:8080 pytest tests/api -q`
   - `cd tests/ui && WEB_BASE_URL=http://localhost:3000 API_BASE_URL=http://localhost:8080 npx playwright test`

## 3. Build
6. Change `services/` until **every** test passes, new and old. Never edit a test or the spec
   to get there; if one is wrong, stop and explain.
7. Click through each [ui] criterion in the browser and show the user screenshots.
8. Set the spec to `status: implemented`. Commit everything: `<ID>: implement <feature>`.

## 4. Stage on GKE and run the full regression
// turbo
9. `scripts/sandbox.sh all`: builds the images for this commit, stages the app as pods in
   `dev-<repo>-<branch>`, runs **all** tests in a test pod, prints `Sandbox result: ...`.
10. Red: read `reports/<namespace>/`, fix, commit, repeat step 9. Never open a PR on red.

## 5. Pull request with evidence
11. `git push -u origin HEAD`.
12. Write `.tmp/pr.md` from `.github/pull_request_template.md` (spec, `Closes #<issue>`,
    criteria covered, the sandbox result line). Show it, then
    `gh pr create --base main --title "<ID>: <title>" --body-file .tmp/pr.md`.
// turbo
13. `scripts/sandbox.sh publish`: posts the sandbox result as a commit status and a PR comment
    listing every test and its criterion.
14. **Leave the sandbox running** (demo mode): do NOT run `scripts/sandbox.sh down`.
    Tell the user the namespace name so they can show it on GKE. It is removed by
    `scripts/sandbox.sh down` when they are done, or by the cleanup workflow after 24 hours.
    <!-- Normal mode: restore the line below to delete the sandbox straight away.
    // turbo
    14. `scripts/sandbox.sh down`.
    -->
15. Print the PR URL. CI now repeats the checks independently; a person reviews and merges.
