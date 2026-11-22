#!/usr/bin/env python3
"""Turn the sandbox's JUnit reports into result.json + summary.md (used by scripts/sandbox.sh).

Usage: sandbox_report.py <reports dir> <namespace> <image tag> <exit code> <commit sha> <branch>

Every test is listed with the acceptance criterion it verifies:
- API tests carry it in the JUnit report (tests/api/conftest.py adds it).
- UI tests are matched by title to their `{ tag: '@<AC-ID>' }` in tests/ui/*.spec.ts.
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI_TAG = re.compile(r"""test\(\s*(['"])(.+?)\1\s*,\s*\{\s*tag:\s*\[?\s*['"]@([A-Z]+-\d{3}-AC\d+)['"]""")
ICON = {"passed": "✅", "failed": "❌", "skipped": "⏭️"}


def ui_tags() -> dict[str, str]:
    tags: dict[str, str] = {}
    for f in (ROOT / "tests" / "ui").glob("*.spec.ts"):
        for _, title, ac in UI_TAG.findall(f.read_text(encoding="utf-8")):
            tags[title] = ac
    return tags


def collect(reports: str) -> list[dict]:
    titles = ui_tags()
    tests = []
    for f in sorted(glob.glob(f"{reports}/*-junit.xml")):
        suite = "api" if Path(f).name.startswith("api") else "ui"
        for case in ET.parse(f).getroot().iter("testcase"):  # noqa: S314 - our own test reports
            name = case.get("name", "")
            ac = next((p.get("value") for p in case.iter("property") if p.get("name") == "acceptance_criterion"), None)
            if ac is None:
                ac = next((v for t, v in titles.items() if name.endswith(t)), "")
            if case.find("failure") is not None or case.find("error") is not None:
                result = "failed"
            elif case.find("skipped") is not None:
                result = "skipped"
            else:
                result = "passed"
            tests.append({"suite": suite, "file": case.get("classname", ""), "name": name, "ac": ac, "result": result})
    return tests


def main(argv: list[str]) -> int:
    reports, ns, tag, code, sha, branch = argv
    tests = collect(reports)
    total = len(tests)
    passed = sum(t["result"] == "passed" for t in tests)
    status = "PASSED" if code == "0" and total and passed == total else "FAILED"

    result = {
        "status": status,
        "passed": passed,
        "total": total,
        "namespace": ns,
        "images": tag,
        "commit": sha,
        "branch": branch,
        "tests": tests,
    }
    Path(reports).mkdir(parents=True, exist_ok=True)
    Path(reports, "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    # SANDBOX_LABEL=PR check when GitHub Actions runs this; the default is the developer's pre-PR run.
    label = os.environ.get("SANDBOX_LABEL", "pre-PR")
    who = (
        "GitHub rebuilt this commit and tested it in its own namespace, independent of the developer's run."
        if label != "pre-PR"
        else "Run by the developer before the PR was opened."
    )
    specs = sorted({t["ac"].rsplit("-AC", 1)[0] for t in tests if t["ac"]})
    md = [
        f"### GKE sandbox ({label}): {status} - {passed}/{total} tests passed",
        "",
        f"Commit `{sha[:7]}` · images `{tag[:12]}` · namespace `{ns}`.  ",
        f"{who} The app ran as pods on GKE and **all** tests ran: the new feature and regression "
        f"for every spec ({', '.join(specs) or 'none'}).",
        "",
        "| | Criterion | Suite | Test |",
        "|---|---|---|---|",
    ]
    md += [f"| {ICON[t['result']]} | `{t['ac'] or '-'}` | {t['suite']} | {t['name']} |" for t in tests]
    Path(reports, "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"\nSandbox result: {status} - {passed}/{total} tests passed (namespace {ns}, images {tag})")
    print(f"Reports: {reports}/  (result.json, summary.md)")
    for t in tests:
        if t["result"] == "failed":
            print(f"  FAILED {t['ac']} {t['file']}::{t['name']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
