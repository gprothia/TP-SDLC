#!/usr/bin/env python3
"""SLO budget for a release, and the canary verdict (standards/slo.md SLO-1, SLO-3, SLO-4).

check_slo.py target [spec files...]
    The strictest ```slo block among the given specs (defaults 300 ms / 1% if none).
    Prints JSON: {"p95_latency_ms", "error_rate_pct", "from": [spec ids]}.

check_slo.py judge <load.json> --p95 <ms> --err <pct> [--track canary] [--min-samples 100] [--md out.md]
    Compares one track of a tools/loadgen.py result with the budget. Prints PASS or FAIL
    (exit 0 / 1). Too few samples is a FAIL: no evidence, no release.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT = {"p95_latency_ms": 300.0, "error_rate_pct": 1.0}
SLO_BLOCK = re.compile(r"```slo\s*\n(.*?)```", re.S)
FIELD = re.compile(r"^\s*(p95_latency_ms|error_rate_pct)\s*:\s*([\d.]+)", re.M)


def spec_slo(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    block = SLO_BLOCK.search(text)
    if not block:
        return None
    values = {k: float(v) for k, v in FIELD.findall(block.group(1))}
    return values if len(values) == 2 else None


def target(files: list[str]) -> dict:
    found = {}
    for f in files:
        p = Path(f)
        if p.suffix == ".md" and p.exists() and not p.name.startswith("_") and (slo := spec_slo(p)):
            found[p.stem.split("-", 2)[0] + "-" + p.stem.split("-", 2)[1]] = slo
    if not found:
        return {**DEFAULT, "from": ["the default in standards/slo.md"]}
    return {
        "p95_latency_ms": min(s["p95_latency_ms"] for s in found.values()),
        "error_rate_pct": min(s["error_rate_pct"] for s in found.values()),
        "from": sorted(found),
    }


def judge(load: dict, p95: float, err: float, track: str, min_samples: int) -> tuple[bool, str]:
    tracks = load.get("tracks", {})
    t = tracks.get(track)
    stable = tracks.get("stable")
    lines = [
        "| | Budget (SLO) | " + ("Stable | " if stable and track != "stable" else "") + f"{track.capitalize()} |",
        "|---|---|" + ("---|" if stable and track != "stable" else "") + "---|",
    ]
    if not t or t["count"] < min_samples:
        n = t["count"] if t else 0
        return False, f"**FAIL**: only {n} {track} requests measured (need {min_samples}). No evidence, no release."

    ok_p95 = t["p95_ms"] <= p95
    ok_err = t["error_pct"] <= err

    def row(name: str, budget: str, key: str, ok: bool, unit: str) -> str:
        s = f"{stable[key]}{unit} | " if stable and track != "stable" else ""
        return f"| {name} | ≤ {budget}{unit} | {s}**{t[key]}{unit}** {'✅' if ok else '❌'} |"

    lines.append(row("p95 latency", f"{p95:g}", "p95_ms", ok_p95, " ms"))
    lines.append(row("Error rate", f"{err:g}", "error_pct", ok_err, "%"))
    lines.append(
        f"| Requests measured | ≥ {min_samples} | "
        + (f"{stable['count']} | " if stable and track != "stable" else "")
        + f"{t['count']} |"
    )
    worst = sorted(t["endpoints"].items(), key=lambda kv: kv[1]["p95_ms"], reverse=True)
    lines += ["", f"Slowest {track} endpoints:", "", "| Endpoint | Requests | p95 | Errors |", "|---|---|---|---|"]
    lines += [f"| `{k}` | {v['count']} | {v['p95_ms']} ms | {v['error_pct']}% |" for k, v in worst[:5]]
    passed = ok_p95 and ok_err
    verdict = "**PASS**: within budget" if passed else "**FAIL**: over budget"
    return passed, verdict + "\n\n" + "\n".join(lines)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("target")
    t.add_argument("files", nargs="*")
    j = sub.add_parser("judge")
    j.add_argument("load")
    j.add_argument("--p95", type=float, required=True)
    j.add_argument("--err", type=float, required=True)
    j.add_argument("--track", default="canary")
    j.add_argument("--min-samples", type=int, default=100)
    j.add_argument("--md")
    a = ap.parse_args(argv)

    if a.cmd == "target":
        print(json.dumps(target(a.files)))
        return 0
    passed, md = judge(json.loads(Path(a.load).read_text()), a.p95, a.err, a.track, a.min_samples)
    if a.md:
        Path(a.md).write_text(md + "\n", encoding="utf-8")
    print(md)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
