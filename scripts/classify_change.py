#!/usr/bin/env python3
"""Is a merged PR a standard change? (standards/release.md REL-2, REL-5)

A standard change goes to production as a canary with no approval meeting. Anything else
waits for a named approver in the GitHub "production" environment. The rule is mechanical,
so the same PR always gets the same answer, with the reasons printed.

  classify_change.py --files changed.txt --tests <check conclusion> --spec-check <0|1>
                     [--labels "a,b"] [--pr <n>]

Prints JSON {"standard": bool, "reasons": [...], "gated_files": [...]}.
"""

from __future__ import annotations

import argparse
import json
import sys

# Changing any of these is never routine: the rules, production, or the release gate itself.
GATED = (
    "standards",  # the pinned SDLC Standards version (a submodule: the path has no slash)
    "standards/",
    ".gitmodules",
    "ruff.toml",
    "deploy/prod/",
    ".github/workflows/release.yml",
    ".github/CODEOWNERS",
    "scripts/classify_change.py",
    "scripts/check_slo.py",
    "scripts/prod.sh",
    "tools/loadgen.py",
)
FORCE_LABEL = "needs-approval"


def classify(files: list[str], tests: str, spec_ok: bool, labels: list[str], pr: str) -> dict:
    reasons = []
    ok = True

    def check(passed: bool, yes: str, no: str) -> None:
        nonlocal ok
        reasons.append(("✅ " + yes) if passed else ("❌ " + no))
        ok = ok and passed

    check(bool(pr), f"Merged through pull request #{pr}", "No pull request found for this commit (direct push)")
    check(spec_ok, "Specs pass standards/checks/check_spec.py", "Specs fail standards/checks/check_spec.py")
    check(
        tests == "success",
        "All tests passed in the PR's GKE sandbox (check: Spec acceptance tests)",
        f"PR's GKE sandbox tests are not green (check: Spec acceptance tests = {tests or 'missing'})",
    )
    gated = sorted(f for f in files if f.startswith(GATED))
    check(
        not gated,
        "Touches no standards, production setup or release-gate files",
        "Touches gated files: " + ", ".join(f"`{f}`" for f in gated),
    )
    check(
        FORCE_LABEL not in labels,
        f"No `{FORCE_LABEL}` label",
        f"A reviewer added the `{FORCE_LABEL}` label",
    )
    return {"standard": ok, "reasons": reasons, "gated_files": gated}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", required=True, help="file with one changed path per line")
    ap.add_argument("--tests", default="")
    ap.add_argument("--spec-check", default="1")
    ap.add_argument("--labels", default="")
    ap.add_argument("--pr", default="")
    a = ap.parse_args(argv)
    files = [line.strip() for line in open(a.files, encoding="utf-8") if line.strip()]
    labels = [x.strip() for x in a.labels.split(",") if x.strip()]
    print(json.dumps(classify(files, a.tests, a.spec_check == "0", labels, a.pr)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
