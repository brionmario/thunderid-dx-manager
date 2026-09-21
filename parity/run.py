"""Loads configuration, runs the analysis, and returns everything the report needs."""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .analyze import Analyzer
from .product import discover, extra_operation_capabilities
from .sdk import SdkIndex, TestCorpus


def _git(repo: Path, *args) -> str:
    try:
        out = subprocess.run(["git", "-C", str(repo), *args],
                             capture_output=True, text=True, timeout=15)
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def provenance(repo: Path) -> dict:
    """What exactly was measured, so a report can be traced back to commits."""
    return {
        "path": str(repo),
        "commit": _git(repo, "rev-parse", "--short", "HEAD") or "unknown",
        "branch": _git(repo, "rev-parse", "--abbrev-ref", "HEAD") or "unknown",
        "date": _git(repo, "log", "-1", "--format=%cs") or "",
        "remote": _git(repo, "remote", "get-url", "origin"),
    }


def load(config_path: Path):
    cfg = yaml.safe_load(config_path.read_text())
    base = config_path.parent

    def resolve(p):
        p = Path(p)
        return p if p.is_absolute() else (base / p).resolve()

    product = resolve(cfg["product"])
    missing = [str(product)] if not product.exists() else []

    indexes, sdk_meta = {}, []
    for spec in cfg["sdks"]:
        spec = dict(spec)
        spec["path"] = str(resolve(spec["path"]))
        if not Path(spec["path"]).exists():
            missing.append(spec["path"])
            continue
        indexes[spec["id"]] = SdkIndex(spec)
        sdk_meta.append({"id": spec["id"], "label": spec["label"],
                         **provenance(Path(spec["path"]))})
    if missing:
        raise SystemExit("Source checkout not found:\n  " + "\n  ".join(missing))

    overrides = {}
    ov_path = base / "catalogue" / "overrides.yaml"
    if ov_path.exists():
        overrides = (yaml.safe_load(ov_path.read_text()) or {}).get("overrides") or {}

    caps = discover(product, cfg["sources"])
    caps += extra_operation_capabilities(
        indexes, [c for c in caps if c.axis == "surface"], overrides)
    product_tests = TestCorpus(product, cfg["sources"].get("product_tests"))
    analyzer = Analyzer(caps, indexes, overrides, product_tests)
    rows = analyzer.run()

    return {
        "rows": rows,
        "sdks": sdk_meta,
        "product": provenance(product),
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "stale_overrides": analyzer.stale_overrides(),
        "product_test_files": len(product_tests.files),
    }
