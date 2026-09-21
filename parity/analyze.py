"""Joins what the product asks for against what each SDK provides.

The rule everywhere is the same: a cell is `supported` only when there is evidence in the
SDK's own source. Where no detector can reach a verdict the cell is `unknown`, which reads
as an open question in the report and is listed as work for a human. Guessing `supported`
would close a gap nobody then looks at, which is the failure this whole tool exists to
prevent.
"""

from __future__ import annotations

from .model import (MISSING, NOT_APPLICABLE, PARTIAL, SUPPORTED, UNDETERMINED,
                    Finding, Part, Row)
from .sdk import norm

# Wire input types that an executor's declared inputs may name.
WIRE_TYPE_SUFFIXES = ("_INPUT", "SELECT", "HIDDEN")

# Tokens too common to prove anything when found in a test file. Matching "text" or
# "action" in a spec says nothing about whether the capability is exercised.
GENERIC_TOKENS = {
    "text", "select", "hidden", "action", "image", "stack", "timer", "icon", "block",
    "custom", "divider", "code", "state", "consent", "mode", "storage", "endpoints",
    "scopes", "discovery", "preferences", "components", "extensions", "number", "date",
}


def _wire_types(cap):
    return sorted({t for _, t in cap.inputs if t.endswith(WIRE_TYPE_SUFFIXES)})


def _identifiers(cap):
    return sorted({i for i, _ in cap.inputs})


def _test_terms(cap):
    """What to look for in an end-to-end suite to claim this capability is exercised.

    Each term is (term, word-boundary?). Wire constants and identifiers are matched whole;
    operation names are matched loosely, because a test calls a page object's
    clickSignInButton rather than the SDK's signIn directly.
    """
    terms = []
    if cap.axis in ("input", "element"):
        terms.append((cap.wire, True))
        # A Maestro flow references the field by its identifier, never by the wire type,
        # so the type's own stem is the only bridge between the two.
        stem = cap.wire.lower().replace("_input", "").replace("_select", "")
        if len(stem) >= 3 and stem not in GENERIC_TOKENS:
            terms.append((stem, True))
    elif cap.axis == "executor":
        for name, _ in cap.inputs:
            if name.lower() not in GENERIC_TOKENS:
                terms.append((name, True))
        for t in _wire_types(cap):
            terms.append((t, True))
    elif cap.axis in ("surface", "extra"):
        terms.append((cap.key, False))
    elif cap.axis == "config":
        if cap.key.lower() not in GENERIC_TOKENS:
            terms.append((cap.key, True))
    return [(t, w) for t, w in terms if t]


class Analyzer:
    def __init__(self, capabilities, indexes, overrides, product_tests=None):
        self.capabilities = capabilities
        self.indexes = indexes                  # {sdk id: SdkIndex}
        self.overrides = overrides or {}
        self.product_tests = product_tests      # TestCorpus for the server's own suites
        self.used_overrides = set()

    def _ov(self, cap):
        key = cap.uid
        if key in self.overrides:
            self.used_overrides.add(key)
            return self.overrides[key] or {}
        return {}

    # ------------------------------------------------------------------ per-axis rules

    def _literal(self, index, wire):
        hits = index.find_literal(wire)
        part = Part(wire, "wire constant", bool(hits), hits)
        if hits:
            return Finding(SUPPORTED, hits, "", [part])
        return Finding(MISSING, [], f"No source in {index.label} quotes \"{wire}\".", [part])

    def _surface(self, index, cap, ov):
        methods = index.methods()
        names = [cap.key] + list(ov.get("aliases") or [])
        for n in names:
            hit = methods.get(norm(n))
            if hit:
                note = "" if norm(n) == norm(cap.key) else f"Implemented as {n}."
                return Finding(SUPPORTED, [hit], note,
                               [Part(n, "client operation", True, [hit])])
        parts = [Part(n, "client operation", False, []) for n in names]
        if not methods:
            return Finding(UNDETERMINED, [], f"No client file configured for {index.label}.", parts)
        return Finding(MISSING, [], f"Not on {index.label}'s client surface.", parts,
                       match_mode="any" if len(names) > 1 else "all")

    def _config(self, index, cap):
        scoped = index.config_files()
        hits = index.find_identifier(cap.key, paths=scoped) if scoped else []
        if hits:
            return Finding(SUPPORTED, hits, "",
                           [Part(cap.key, "configuration key", True, hits)])
        # A key may be handled outside a file named "config"; look wider before failing,
        # and say that the evidence is weaker when it turns up there.
        hits = index.find_identifier(cap.key)
        if hits:
            return Finding(SUPPORTED, hits, "Found outside the configuration model.",
                           [Part(cap.key, "configuration key", True, hits)])
        return Finding(MISSING, [], f"No configuration key named {cap.key}.",
                       [Part(cap.key, "configuration key", False, [])])

    def _extra(self, index, cap, sid):
        where = getattr(cap, "places", {}).get(sid)
        part = Part(cap.name, "client operation", bool(where), [where] if where else [])
        if where:
            return Finding(SUPPORTED, [where], "", [part])
        return Finding(MISSING, [], f"Not exposed by {index.label}.", [part])

    def _executor(self, index, cap, ov):
        detect = ov.get("detect") or {}

        # A detector says "any one of these proves it", because an executor with no fixed
        # input list is driven by whichever mechanism the platform offers.
        if detect:
            parts = []
            for lit in detect.get("any_literal") or []:
                hits = index.find_literal(lit)
                parts.append(Part(lit, "wire constant", bool(hits), hits))
            for ident in detect.get("any_identifier") or []:
                hits = index.find_identifier(ident)
                parts.append(Part(ident, "input identifier", bool(hits), hits))
            found = [p for p in parts if p.found]
            if found:
                return Finding(SUPPORTED, found[0].evidence, "", parts, match_mode="any")
            names = ", ".join(p.name for p in parts)
            return Finding(MISSING, [], f"None of {names} appear in {index.label}.",
                           parts, match_mode="any")

        # Otherwise the executor's own declared inputs are the contract: the SDK must
        # render each input type and submit each identifier, or the step stalls.
        parts = []
        for t in _wire_types(cap):
            hits = index.find_literal(t)
            parts.append(Part(t, "input type", bool(hits), hits))
        for i in _identifiers(cap):
            hits = index.find_identifier(i)
            parts.append(Part(i, "input identifier", bool(hits), hits))

        if not parts:
            return Finding(UNDETERMINED, [],
                           "Builds its prompt at runtime and has no detector in "
                           "catalogue/overrides.yaml.")

        missing = [p.name for p in parts if not p.found]
        evidence = [e for p in parts if p.found for e in p.evidence[:1]]
        if not missing:
            return Finding(SUPPORTED, evidence, "", parts)
        # Partial support is the interesting case: the SDK drives some of the step but
        # would stall on the rest, which is exactly how a flow breaks in production.
        status = PARTIAL if len(missing) < len(parts) else MISSING
        return Finding(status, evidence, "Does not handle " + ", ".join(missing) + ".", parts)

    # ------------------------------------------------------------------------- driver

    def run(self) -> list:
        rows = []
        for cap in self.capabilities:
            ov = self._ov(cap)
            row = Row(capability=cap)
            if ov.get("note"):
                cap.notes = ov["note"].strip()

            # Server-internal and informational capabilities are carried for visibility
            # but never scored: they place no obligation on an SDK.
            scored = cap.client_facing and not ov.get("informational")

            for sid, index in self.indexes.items():
                if not scored:
                    row.findings[sid] = Finding(NOT_APPLICABLE, [], cap.notes or "Not an SDK obligation.")
                    continue
                na = (ov.get("na") or {}).get(sid)
                if na:
                    row.findings[sid] = Finding(NOT_APPLICABLE, [], na)
                    continue
                if cap.axis in ("input", "element"):  # noqa: E501 - dispatch below
                    row.findings[sid] = self._literal(index, cap.wire)
                elif cap.axis == "surface":
                    row.findings[sid] = self._surface(index, cap, ov)
                elif cap.axis == "config":
                    row.findings[sid] = self._config(index, cap)
                elif cap.axis == "extra":
                    row.findings[sid] = self._extra(index, cap, sid)
                elif cap.axis == "executor":
                    row.findings[sid] = self._executor(index, cap, ov)
                else:
                    row.findings[sid] = Finding(UNDETERMINED, [], "No rule for this axis.")

                # Implementation and test coverage are separate claims. An SDK can render
                # an input nothing ever exercises, and that is worth seeing on its own.
                finding = row.findings[sid]
                for term, word in _test_terms(cap):
                    for where in index.find_in_tests(term, word=word, limit=2):
                        finding.tests.append((term, where))
            # The server's own suites, scored once per capability rather than per SDK.
            row.product_tests = []
            if scored and self.product_tests:
                seen = set()
                for term, word in _test_terms(cap):
                    for where in self.product_tests.find(term, word=word, limit=2):
                        if where not in seen:
                            seen.add(where)
                            row.product_tests.append((term, where))

            row.scored = scored
            rows.append(row)
        return rows

    def stale_overrides(self) -> list:
        return sorted(set(self.overrides) - self.used_overrides)
