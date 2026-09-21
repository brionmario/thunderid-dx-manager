"""Shared vocabulary for the parity matrix.

A Capability is one row of the report: one thing the product can ask of an SDK. It is
discovered from the product repo, never hand-listed, so a capability that appears
upstream shows up here whether or not anyone remembered to write it down.

A Finding is one cell: what a single SDK does about a single capability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# Axes, in report order. The key is what `--axis` takes on the command line.
AXES = {
    "executor": "Flow executors",
    "input": "Flow input types",
    "element": "Flow element types",
    "surface": "Client surface",
    "config": "Configuration keys",
    "extra": "Operations beyond the specification",
}

# Cell verdicts.
SUPPORTED = "supported"      # evidence found in the SDK
MISSING = "missing"          # the product can emit this and the SDK shows no sign of handling it
NOT_APPLICABLE = "na"        # cannot apply on this platform; requires a stated reason
PARTIAL = "partial"          # some of what the capability needs is handled, not all
UNDETERMINED = "unknown"     # no detector can decide this one; needs a human, and says so


@dataclass
class Capability:
    """One thing the product can ask of an SDK."""

    axis: str
    key: str                              # stable id, unique within the axis
    name: str                             # what to show in the report
    origin: str                           # "file:line" in the product repo, so a row is checkable
    group: str = ""                       # subheading within the axis
    wire: Optional[str] = None            # the literal that crosses the wire, when there is one
    required: bool = True                 # MUST in the spec, vs SHOULD/MAY
    client_facing: bool = True            # False => server-internal, never reaches an SDK
    inputs: list = field(default_factory=list)   # [(identifier, wire type)] for executors
    notes: str = ""

    @property
    def uid(self) -> str:
        return f"{self.axis}:{self.key}"


@dataclass
class Finding:
    """What one SDK does about one capability."""

    status: str
    evidence: list = field(default_factory=list)   # ["path:line", ...]
    reason: str = ""                               # required for na / unknown


@dataclass
class Row:
    capability: Capability
    findings: dict = field(default_factory=dict)   # sdk id -> Finding

    def count(self, status: str) -> int:
        return sum(1 for f in self.findings.values() if f.status == status)

    @property
    def is_gap(self) -> bool:
        return self.count(MISSING) + self.count(PARTIAL) > 0

    @property
    def is_total_gap(self) -> bool:
        """Nothing implements it. Usually means the product moved and no SDK followed."""
        return self.count(SUPPORTED) == 0 and self.count(MISSING) > 0
