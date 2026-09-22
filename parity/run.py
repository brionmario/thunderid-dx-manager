"""Loads configuration, runs the analysis, and returns everything the report needs."""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .analyze import Analyzer
from .github import collect as collect_github
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


def load(config_path: Path, sources_root=None):
    """Read the configuration and measure everything it points at.

    `sources_root` repoints every entry at DIR/<repo name>, so a checkout layout built by a
    workflow uses the same configuration as a local one. Keeping one file is the point: two
    drifted once, and CI quietly reported no end-to-end coverage anywhere as a result.
    """
    cfg = yaml.safe_load(config_path.read_text())
    base = config_path.parent
    root = Path(sources_root).resolve() if sources_root else None

    def resolve(p):
        p = Path(p)
        return p if p.is_absolute() else (base / p).resolve()

    def locate(entry_path, repo):
        if root is not None:
            if not repo:
                raise SystemExit(
                    f"--sources-root needs a repo for every entry; {entry_path} has none.")
            return root / repo.split("/")[-1]
        return resolve(entry_path)

    product = locate(cfg["product"], cfg.get("product_repo"))
    missing = [str(product)] if not product.exists() else []

    indexes, sdk_meta, warnings = {}, [], []
    for spec in cfg["sdks"]:
        spec = dict(spec)
        spec["path"] = str(locate(spec["path"], spec.get("repo")))
        if not Path(spec["path"]).exists():
            missing.append(spec["path"])
            continue
        index = SdkIndex(spec)
        indexes[spec["id"]] = index
        # A suite that is declared and indexes nothing is a configuration error, not an
        # absence of tests. Left silent it reads as "nothing is tested", which is the most
        # misleading thing the report could say.
        if spec.get("e2e") and not index.e2e_files:
            warnings.append(
                f"{spec['label']}: no test files found under "
                f"{', '.join(spec['e2e'])} - every E2E result for it will read as zero.")
        sdk_meta.append({"id": spec["id"], "label": spec["label"],
                         **provenance(Path(spec["path"]))})
    if missing:
        raise SystemExit("Source checkout not found:\n  " + "\n  ".join(missing))

    overrides = {}
    ov_path = base / "catalogue" / "overrides.yaml"
    if ov_path.exists():
        overrides = (yaml.safe_load(ov_path.read_text()) or {}).get("overrides") or {}

    live = collect_github(cfg)
    warnings.extend(live["errors"])

    caps = discover(product, cfg["sources"])
    caps += extra_operation_capabilities(
        indexes, [c for c in caps if c.axis == "surface"], overrides)
    product_tests = TestCorpus(product, cfg["sources"].get("product_tests"))
    if cfg["sources"].get("product_tests") and not product_tests.files:
        warnings.append("Product: no test files found under "
                        f"{', '.join(cfg['sources']['product_tests'])}.")
    analyzer = Analyzer(caps, indexes, overrides, product_tests)
    rows = analyzer.run()

    return {
        "rows": rows,
        "sdks": sdk_meta,
        "product": provenance(product),
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "stale_overrides": analyzer.stale_overrides(),
        "product_test_files": len(product_tests.files),
        "warnings": warnings,
        "repo_url": cfg.get("repo_url", ""),
        "pull_requests": live["pull_requests"],
        "issues": live["issues"],
        "indexes": indexes,
    }
