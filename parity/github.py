"""Collects the live side of the dashboard: open pull requests and DX issues.

Parity is derived from source and is true of a commit. These two are true of a moment, so
they are fetched when the report is generated and stamped with that time. Everything goes
through the `gh` CLI, which already holds the credentials locally and on a runner, so this
module never handles a token itself.

A failure here degrades rather than fails: the section says it could not be fetched, and a
warning goes to the top of the page. An empty list is a real answer and must not be
confused with a broken one, because "no open pull requests" and "could not ask" look
identical once rendered.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone


class GitHubUnavailable(RuntimeError):
    pass


def _gh(args, timeout=60):
    if not shutil.which("gh"):
        raise GitHubUnavailable("the gh CLI is not installed")
    proc = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip().splitlines()
        raise GitHubUnavailable(detail[-1] if detail else "gh exited non-zero")
    return json.loads(proc.stdout or "[]")


def _age_days(iso: str) -> int:
    when = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - when).days


PR_FIELDS = ("number,title,author,createdAt,updatedAt,isDraft,labels,"
             "reviewDecision,additions,deletions,url")


def pull_requests(repos, stale_after=14) -> list:
    """Open pull requests across the tracked repositories, newest activity first."""
    out = []
    for repo in repos:
        rows = _gh(["pr", "list", "--repo", repo, "--state", "open",
                    "--limit", "200", "--json", PR_FIELDS])
        for pr in rows:
            out.append({
                "repo": repo.split("/")[-1],
                "number": pr["number"],
                "title": pr["title"],
                "url": pr["url"],
                "author": (pr.get("author") or {}).get("login", "unknown"),
                "draft": pr.get("isDraft", False),
                "review": pr.get("reviewDecision") or "",
                "labels": [l["name"] for l in pr.get("labels") or []],
                "opened_days": _age_days(pr["createdAt"]),
                "idle_days": _age_days(pr["updatedAt"]),
                "additions": pr.get("additions", 0),
                "deletions": pr.get("deletions", 0),
            })
            out[-1]["stale"] = out[-1]["idle_days"] >= stale_after and not out[-1]["draft"]
    out.sort(key=lambda p: (-p["idle_days"], p["repo"], p["number"]))
    return out


ISSUE_FIELDS = "number,title,labels,milestone,assignees,createdAt,updatedAt,url,comments"


def issues(repo, labels, stale_after=60) -> list:
    """Open issues in one repository carrying every one of `labels`."""
    args = ["issue", "list", "--repo", repo, "--state", "open",
            "--limit", "300", "--json", ISSUE_FIELDS]
    for label in labels:
        args += ["--label", label]
    out = []
    for issue in _gh(args):
        names = [l["name"] for l in issue.get("labels") or []]
        out.append({
            "repo": repo.split("/")[-1],
            "number": issue["number"],
            "title": issue["title"],
            "url": issue["url"],
            "labels": names,
            "kind": next((n for n in names if n.startswith("Type/")), ""),
            "theme": next((n for n in names if n.startswith("Theme/")), ""),
            "priority": next((n for n in names if n.startswith("Priority/")), ""),
            "milestone": (issue.get("milestone") or {}).get("title", ""),
            "assignees": [a["login"] for a in issue.get("assignees") or []],
            # gh returns the comment objects here, not a count.
            "comments": len(issue.get("comments") or []),
            "opened_days": _age_days(issue["createdAt"]),
            "idle_days": _age_days(issue["updatedAt"]),
        })
        out[-1]["stale"] = out[-1]["idle_days"] >= stale_after
    out.sort(key=lambda i: (i["kind"], -i["opened_days"]))
    return out


def collect(cfg) -> dict:
    """Everything the live sections need, with per-section failure kept separate.

    One section failing must not blank the other: they are different calls and a token that
    can read one repository may not read another.
    """
    gh_cfg = (cfg or {}).get("github") or {}
    result = {"pull_requests": None, "issues": None, "errors": []}

    prs = gh_cfg.get("pull_requests") or {}
    if prs.get("repos"):
        try:
            result["pull_requests"] = pull_requests(
                prs["repos"], prs.get("stale_after_days", 14))
        except Exception as exc:
            result["errors"].append(f"Open pull requests could not be fetched: {exc}")

    iss = gh_cfg.get("issues") or {}
    if iss.get("repo"):
        try:
            result["issues"] = issues(
                iss["repo"], iss.get("labels") or [], iss.get("stale_after_days", 60))
        except Exception as exc:
            result["errors"].append(f"Issues could not be fetched: {exc}")

    return result
