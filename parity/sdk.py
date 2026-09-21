"""Collects evidence from an SDK checkout.

Evidence is always a file and a line, never a yes/no, so every cell in the report can be
clicked through to the code that justifies it. Where no detector can decide a cell, this
module says so rather than guessing: an unproven "supported" is worse than an open
question, because it closes a gap nobody then looks at.
"""

from __future__ import annotations

import re
from pathlib import Path


class SdkIndex:
    """Every source file of one SDK, read once."""

    def __init__(self, spec: dict):
        self.id = spec["id"]
        self.label = spec["label"]
        self.root = Path(spec["path"])
        self.globs = spec.get("globs", [])
        self.exclude = spec.get("exclude", [])
        client = spec.get("client")
        self.client_rels = [client] if isinstance(client, str) else list(client or [])
        self.method_pattern = spec.get("method_pattern")
        self.e2e_dirs = spec.get("e2e", [])
        self.spellings = {}
        self.files = self._collect()
        self.texts = {p: p.read_text(encoding="utf-8", errors="replace") for p in self.files}
        self.e2e_files = self._collect_e2e()
        self.e2e_texts = {p: p.read_text(encoding="utf-8", errors="replace")
                          for p in self.e2e_files}
        self._methods = None

    # ------------------------------------------------------------------ file collection

    def _excluded(self, path: Path) -> bool:
        s = str(path)
        return any(frag in s for frag in self.exclude)

    def _collect(self) -> list:
        out = []
        for g in self.globs:
            for p in self.root.rglob(g):
                if p.is_file() and not self._excluded(p):
                    out.append(p)
        return sorted(set(out))

    # End-to-end suites are their own corpus. A Maestro flow is YAML and a Playwright spec
    # is TypeScript, so the SDK's own source globs would miss half of them; and a match in a
    # test proves the behaviour is exercised, which is a different claim from a match in the
    # implementation.
    E2E_SUFFIXES = (".ts", ".tsx", ".js", ".yaml", ".yml", ".swift", ".kt", ".dart")
    E2E_SKIP = (".thunderid-server", "/node_modules/", "/report", "/.git/")

    def _collect_e2e(self) -> list:
        out = []
        for d in self.e2e_dirs:
            base = self.root / d
            if not base.exists():
                continue
            for p in base.rglob("*"):
                if not p.is_file() or p.suffix not in self.E2E_SUFFIXES:
                    continue
                if any(frag in str(p) for frag in self.E2E_SKIP):
                    continue
                out.append(p)
        return sorted(set(out))

    def find_in_tests(self, term: str, word: bool = True, limit: int = 5) -> list:
        """Where an end-to-end test references a term."""
        rx = (re.compile(r"\b" + re.escape(term) + r"\b") if word
              else re.compile(re.escape(term), re.I))
        hits = []
        for p, text in self.e2e_texts.items():
            m = rx.search(text)
            if m:
                hits.append(f"{self.rel(p)}:{text.count(chr(10), 0, m.start()) + 1}")
            if len(hits) >= limit:
                break
        return hits

    def rel(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.root))
        except ValueError:
            return str(path)

    # ----------------------------------------------------------------------- detectors

    def find_literal(self, wire: str, limit: int = 6) -> list:
        """Files quoting a wire constant verbatim, e.g. 'OTP_INPUT'."""
        pattern = re.compile(r"""['"]""" + re.escape(wire) + r"""['"]""")
        hits = []
        for p, text in self.texts.items():
            if wire not in text:
                continue
            for m in pattern.finditer(text):
                hits.append(f"{self.rel(p)}:{text.count(chr(10), 0, m.start()) + 1}")
                break
            if len(hits) >= limit:
                break
        return hits

    @property
    def client_paths(self) -> list:
        return [p for p in (self.root / r for r in self.client_rels) if p.exists()]

    def methods(self) -> dict:
        """Public operations on the SDK's client, as {normalized name: 'file:line'}.

        `spellings` keeps the name as written, so a report can show buildSignInURL rather
        than the folded key used for matching.
        """
        if self._methods is not None:
            return self._methods
        out, self.spellings = {}, {}
        if self.method_pattern:
            rx = re.compile(self.method_pattern, re.M)
            for p in self.client_paths:
                text = p.read_text(encoding="utf-8", errors="replace")
                for m in rx.finditer(text):
                    name = m.group(1)
                    if name in NOT_AN_OPERATION:
                        continue
                    key = norm(name)
                    if key not in out:
                        out[key] = f"{self.rel(p)}:{text.count(chr(10), 0, m.start()) + 1}"
                        self.spellings[key] = name
        self._methods = out
        return out

    def config_files(self) -> list:
        return [p for p in self.files if "config" in p.name.lower()]

    def find_identifier(self, ident: str, paths=None, limit: int = 4) -> list:
        """Whole-word identifier hits, used for configuration keys."""
        rx = re.compile(r"\b" + re.escape(ident) + r"\b")
        hits = []
        for p in (paths if paths is not None else self.files):
            text = self.texts.get(p)
            if not text or ident not in text:
                continue
            m = rx.search(text)
            if m:
                hits.append(f"{self.rel(p)}:{text.count(chr(10), 0, m.start()) + 1}")
            if len(hits) >= limit:
                break
        return hits


# Language keywords and platform boilerplate that the method regex picks up but which are
# not part of anybody's public surface.
NOT_AN_OPERATION = {
    "if", "for", "while", "switch", "return", "get", "set", "init", "constructor",
    "super", "this", "catch", "try", "do", "else", "when", "toString", "hashCode",
    "equals", "copyWith", "dispose", "build", "noSuchMethod", "runtimeType",
}


class TestCorpus:
    """A suite of tests, indexed for reference lookups.

    Used for the product's own integration and end-to-end suites. A capability the server
    tests but no SDK does is the sharpest version of a parity gap: the behaviour is known
    to work and known to be reachable, and no client exercises it.
    """

    SUFFIXES = (".go", ".ts", ".tsx", ".js", ".yaml", ".yml")
    SKIP = ("/node_modules/", "/.git/", "/dist/", "/build/")

    def __init__(self, root: Path, dirs, label: str = "product"):
        self.root, self.label = Path(root), label
        self.files = []
        for d in dirs or []:
            base = self.root / d
            if not base.exists():
                continue
            for p in base.rglob("*"):
                if (p.is_file() and p.suffix in self.SUFFIXES
                        and not any(f in str(p) for f in self.SKIP)):
                    self.files.append(p)
        self.files = sorted(set(self.files))
        self.texts = {p: p.read_text(encoding="utf-8", errors="replace") for p in self.files}

    def rel(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.root))
        except ValueError:
            return str(path)

    def find(self, term: str, word: bool = True, limit: int = 4) -> list:
        rx = (re.compile(r"\b" + re.escape(term) + r"\b") if word
              else re.compile(re.escape(term), re.I))
        hits = []
        for p, text in self.texts.items():
            m = rx.search(text)
            if m:
                hits.append(f"{self.rel(p)}:{text.count(chr(10), 0, m.start()) + 1}")
            if len(hits) >= limit:
                break
        return hits


def norm(name: str) -> str:
    """Fold naming conventions so buildSignInURL, buildSignInUrl and build_sign_in_url match."""
    return re.sub(r"[^a-z0-9]", "", name.lower())
