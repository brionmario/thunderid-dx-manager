"""Command line entry point: python3 -m parity [--html out/index.html] [--json out/parity.json]"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .model import (AXES, MISSING, NOT_APPLICABLE, PARTIAL, SUPPORTED, UNDETERMINED)
from .run import load

STATUS_MARK = {SUPPORTED: "yes", MISSING: "GAP", PARTIAL: "part",
               NOT_APPLICABLE: "n/a", UNDETERMINED: "?"}


def summarize(result, axis_filter=None):
    rows = [r for r in result["rows"] if not axis_filter or r.capability.axis == axis_filter]
    sdks = result["sdks"]
    width = max(len(r.capability.name) for r in rows) + 2

    for axis, title in AXES.items():
        axis_rows = [r for r in rows if r.capability.axis == axis]
        if not axis_rows:
            continue
        print(f"\n== {title} ({len(axis_rows)}) " + "=" * 20)
        print(" " * width + "".join(f"{s['label'][:9]:<11}" for s in sdks))
        for r in sorted(axis_rows, key=lambda r: (not r.is_gap, r.capability.name)):
            cells = "".join(f"{STATUS_MARK[r.findings[s['id']].status]:<11}" for s in sdks)
            print(f"{r.capability.name:<{width}}{cells}")

    print("\n-- coverage --")
    for s in sdks:
        scored = [r for r in rows if r.findings[s["id"]].status != NOT_APPLICABLE]
        ok = sum(1 for r in scored if r.findings[s["id"]].status == SUPPORTED)
        gap = sum(1 for r in scored if r.findings[s["id"]].status == MISSING)
        part = sum(1 for r in scored if r.findings[s["id"]].status == PARTIAL)
        unk = sum(1 for r in scored if r.findings[s["id"]].status == UNDETERMINED)
        pct = (100 * ok / len(scored)) if scored else 0
        print(f"  {s['label']:<12} {pct:5.1f}%   ok={ok:<4} partial={part:<4} gaps={gap:<4} unknown={unk}")


def to_json(result):
    return {
        "generated": result["generated"],
        "product": result["product"],
        "sdks": result["sdks"],
        "staleOverrides": result["stale_overrides"],
        "pullRequests": result.get("pull_requests"),
        "issues": result.get("issues"),
        "capabilities": [
            {
                "axis": r.capability.axis,
                "key": r.capability.key,
                "name": r.capability.name,
                "group": r.capability.group,
                "origin": r.capability.origin,
                "required": r.capability.required,
                "clientFacing": r.capability.client_facing,
                "notes": r.capability.notes,
                "inputs": [{"identifier": i, "type": t} for i, t in r.capability.inputs],
                "sdks": {
                    sid: {
                        "status": f.status,
                        "evidence": f.evidence,
                        "reason": f.reason,
                        "matchMode": f.match_mode,
                        "parts": [
                            {"name": p.name, "kind": p.kind,
                             "found": p.found, "evidence": p.evidence}
                            for p in f.parts
                        ],
                        "tests": [{"term": t, "at": w} for t, w in f.tests],
                    }
                    for sid, f in r.findings.items()
                },
            }
            for r in result["rows"]
        ],
    }


def main():
    ap = argparse.ArgumentParser(prog="parity", description="Cross-SDK capability parity report.")
    ap.add_argument("-c", "--config", default="parity.config.yaml")
    ap.add_argument("--sources-root", metavar="DIR",
                    help="look for every repo under DIR, named after its upstream")
    ap.add_argument("--axis", choices=list(AXES), help="limit the text summary to one axis")
    ap.add_argument("--html", metavar="PATH", help="write the HTML report")
    ap.add_argument("--json", metavar="PATH", help="write the machine-readable report")
    ap.add_argument("--quiet", action="store_true", help="suppress the text summary")
    ap.add_argument("--snapshot", metavar="PATH",
                    help="write this run's verdicts, for a later run to compare against")
    ap.add_argument("--baseline", metavar="PATH",
                    help="a snapshot from an earlier run; the report reports what changed")
    ap.add_argument("--fail-on-regression", action="store_true",
                    help="exit non-zero when a capability an SDK used to handle regressed")
    ap.add_argument("--fail-on-gap", action="store_true",
                    help="exit non-zero when any scored capability is missing everywhere")
    args = ap.parse_args()

    result = load(Path(args.config).resolve(), args.sources_root)

    for w in result["warnings"]:
        print(f"warning: {w}")

    # The comparison has to happen before the snapshot is written, or a run whose snapshot
    # and baseline are the same path would compare against itself and never see a change.
    from . import snapshot as snap
    current = snap.build(result)
    baseline = snap.load(args.baseline) if args.baseline else None
    result["diff"] = snap.diff(baseline, current)
    if args.baseline:
        print(f"since {baseline['generated'] if baseline else 'no baseline'}: "
              f"{snap.summarize(result['diff'])}")

    if not args.quiet:
        summarize(result, args.axis)

    if args.json:
        p = Path(args.json); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(to_json(result), indent=2))
        print(f"\nwrote {p}")

    if args.html:
        from .report import render, render_about, render_issues, render_pulls
        p = Path(args.html); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(render(result))
        print(f"wrote {p}")
        # The explainer is a sibling page, linked from every footer.
        for name, fn in (("pull-requests.html", render_pulls),
                         ("issues.html", render_issues),
                         ("how-it-works.html", render_about)):
            sibling = p.parent / name
            sibling.write_text(fn(result))
            print(f"wrote {sibling}")

    if args.snapshot:
        sp = Path(args.snapshot); sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n")
        print(f"wrote {sp}")

    if args.fail_on_regression and result["diff"].get("regressions"):
        for r in result["diff"]["regressions"]:
            print(f"regression: {r['name']} on {r['sdk']}: {r['from']} -> {r['to']}")
        return 1

    if args.fail_on_gap:
        total = [r for r in result["rows"] if r.is_total_gap]
        if total:
            print(f"\n{len(total)} capability(ies) implemented by no SDK")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
