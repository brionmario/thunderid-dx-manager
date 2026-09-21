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
        self.spellings = {}
        self.files = self._collect()
        self.texts = {p: p.read_text(encoding="utf-8", errors="replace") for p in self.files}
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


def norm(name: str) -> str:
    """Fold naming conventions so buildSignInURL, buildSignInUrl and build_sign_in_url match."""
    return re.sub(r"[^a-z0-9]", "", name.lower())
