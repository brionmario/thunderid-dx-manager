"""Joins what the product asks for against what each SDK provides.

The rule everywhere is the same: a cell is `supported` only when there is evidence in the
SDK's own source. Where no detector can reach a verdict the cell is `unknown`, which reads
as an open question in the report and is listed as work for a human. Guessing `supported`
would close a gap nobody then looks at, which is the failure this whole tool exists to
prevent.
"""

from __future__ import annotations

from .model import (MISSING, NOT_APPLICABLE, PARTIAL, SUPPORTED, UNDETERMINED,
                    Finding, Row)
from .sdk import norm

# Wire input types that an executor's declared inputs may name.
WIRE_TYPE_SUFFIXES = ("_INPUT", "SELECT", "HIDDEN")


def _wire_types(cap):
    return sorted({t for _, t in cap.inputs if t.endswith(WIRE_TYPE_SUFFIXES)})


def _identifiers(cap):
    return sorted({i for i, _ in cap.inputs})


class Analyzer:
    def __init__(self, capabilities, indexes, overrides):
        self.capabilities = capabilities
        self.indexes = indexes                  # {sdk id: SdkIndex}
        self.overrides = overrides or {}
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
        if hits:
            return Finding(SUPPORTED, hits)
        return Finding(MISSING, [], f"No source in {index.label} quotes \"{wire}\".")

    def _surface(self, index, cap, ov):
        methods = index.methods()
        names = [cap.key] + list(ov.get("aliases") or [])
        for n in names:
            hit = methods.get(norm(n))
            if hit:
                note = "" if norm(n) == norm(cap.key) else f"Implemented as {n}."
                return Finding(SUPPORTED, [hit], note)
        if not methods:
            return Finding(UNDETERMINED, [], f"No client file configured for {index.label}.")
        return Finding(MISSING, [], f"Not on {index.label}'s client surface.")

    def _config(self, index, cap):
        scoped = index.config_files()
        hits = index.find_identifier(cap.key, paths=scoped) if scoped else []
        if hits:
            return Finding(SUPPORTED, hits)
        # A key may be handled outside a file named "config"; look wider before failing,
        # and say that the evidence is weaker when it turns up there.
        hits = index.find_identifier(cap.key)
        if hits:
            return Finding(SUPPORTED, hits, "Found outside the configuration model.")
        return Finding(MISSING, [], f"No configuration key named {cap.key}.")

    def _extra(self, index, cap, sid):
        where = getattr(cap, "places", {}).get(sid)
        if where:
            return Finding(SUPPORTED, [where])
        return Finding(MISSING, [], f"Not exposed by {index.label}.")

    def _executor(self, index, cap, ov):
        detect = ov.get("detect") or {}
        evidence, reasons = [], []

        for lit in detect.get("any_literal") or []:
            hits = index.find_literal(lit)
            if hits:
                return Finding(SUPPORTED, hits)
            reasons.append(f'"{lit}"')

        for ident in detect.get("any_identifier") or []:
            hits = index.find_identifier(ident)
            if hits:
                return Finding(SUPPORTED, hits)
            reasons.append(ident)

        if detect:
            return Finding(MISSING, [], "None of " + ", ".join(reasons) + f" appear in {index.label}.")

        # Derived: the executor's own declared inputs must all be handled.
        types, idents = _wire_types(cap), _identifiers(cap)
        missing = []
        for t in types:
            hits = index.find_literal(t)
            evidence.extend(hits[:1])
            if not hits:
                missing.append(t)
        for i in idents:
            hits = index.find_identifier(i)
            evidence.extend(hits[:1])
            if not hits:
                missing.append(i)

        if not types and not idents:
            return Finding(UNDETERMINED, [],
                           "Builds its prompt at runtime and has no detector in "
                           "catalogue/overrides.yaml.")
        if not missing:
            return Finding(SUPPORTED, evidence)
        # Partial support is the interesting case: the SDK drives some of the step but
        # would stall on the rest, which is exactly how a flow breaks in production.
        handled = len(types) + len(idents) - len(missing)
        status = PARTIAL if handled else MISSING
        return Finding(status, evidence, "Does not handle " + ", ".join(missing) + ".")

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
                if cap.axis in ("input", "element"):
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
            row.scored = scored
            rows.append(row)
        return rows

    def stale_overrides(self) -> list:
        return sorted(set(self.overrides) - self.used_overrides)
