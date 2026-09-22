"""Snapshots of a run, and the difference between two of them.

A percentage tells you where things stand and nothing about what moved. The question worth
answering weekly is narrower: did anything that worked last week stop working, and did the
product grow a capability the SDKs have not caught up with. Both need a previous run to
compare against, so each run commits a small record of its verdicts.

The record holds verdicts only, not evidence: it is written every week and kept forever, and
the file paths behind a verdict are the one part that churns without the verdict changing.
"""

from __future__ import annotations

import json
from pathlib import Path

from .model import (MISSING, NOT_APPLICABLE, PARTIAL, SUPPORTED, UNDETERMINED)

# How much a verdict is worth, so a move between two of them has a direction.
RANK = {MISSING: 0, UNDETERMINED: 1, PARTIAL: 2, SUPPORTED: 3, NOT_APPLICABLE: 4}


def build(result) -> dict:
    """The verdicts of one run, in the form kept in the repository."""
    caps = {}
    for row in result["rows"]:
        if not getattr(row, "scored", True):
            continue
        cap = row.capability
        caps[cap.uid] = {
            "axis": cap.axis,
            "name": cap.name,
            "sdks": {sid: f.status for sid, f in row.findings.items()},
        }
    return {
        "generated": result["generated"],
        "product": {k: result["product"][k] for k in ("commit", "branch")},
        "sdks": {s["id"]: s["commit"] for s in result["sdks"]},
        "capabilities": caps,
    }


def load(path) -> dict | None:
    path = Path(path)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) and "capabilities" in data else None


def diff(old: dict, new: dict) -> dict:
    """What changed between two runs.

    Four kinds, and they are not the same thing. A regression is something that worked and
    stopped. A new gap is the product moving ahead of the SDKs, which is expected and still
    has to be caught. An improvement is worth showing so a week's work is visible. A removal
    usually means a capability was renamed upstream, which is worth a look rather than
    silence.
    """
    if not old:
        return {}
    old_caps, new_caps = old.get("capabilities", {}), new.get("capabilities", {})

    regressions, improvements, added, removed = [], [], [], []

    for uid, cap in sorted(new_caps.items()):
        before = old_caps.get(uid)
        if before is None:
            gaps = [sid for sid, st in cap["sdks"].items() if st in (MISSING, PARTIAL)]
            added.append({"uid": uid, "axis": cap["axis"], "name": cap["name"],
                          "gaps": sorted(gaps),
                          "sdks": cap["sdks"]})
            continue
        for sid, status in cap["sdks"].items():
            was = before["sdks"].get(sid)
            if was is None or was == status:
                continue
            move = {"uid": uid, "axis": cap["axis"], "name": cap["name"],
                    "sdk": sid, "from": was, "to": status}
            # NOT_APPLICABLE sits outside the scale: moving to or from it means the
            # capability was reclassified, not that an SDK gained or lost anything.
            if NOT_APPLICABLE in (was, status):
                continue
            (regressions if RANK[status] < RANK[was] else improvements).append(move)

    for uid, cap in sorted(old_caps.items()):
        if uid not in new_caps:
            removed.append({"uid": uid, "axis": cap["axis"], "name": cap["name"]})

    return {
        "baseline": {"generated": old.get("generated", ""),
                     "product": old.get("product", {})},
        "regressions": regressions,
        "added": added,
        "improvements": improvements,
        "removed": removed,
    }


def summarize(d: dict) -> str:
    if not d:
        return "no baseline to compare against"
    new_gaps = sum(1 for a in d["added"] if a["gaps"])
    return (f"{len(d['regressions'])} regression(s), {len(d['added'])} new capability(ies) "
            f"({new_gaps} already short), {len(d['improvements'])} improvement(s), "
            f"{len(d['removed'])} removed")
