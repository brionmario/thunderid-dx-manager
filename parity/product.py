"""Discovers what the product can ask of an SDK.

Everything here reads the ThunderID monorepo. Nothing is hand-listed: the point is that a
new executor, a new input type, or a new row in a specification table turns up in the
report on the next run, without anyone adding it to a list first.
"""

from __future__ import annotations

import re
from pathlib import Path

from .model import Capability

# ----------------------------------------------------------------------------- helpers


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _lineno(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


# --------------------------------------------------------------------------- wire types

CONST_RE = re.compile(r'^\s*(\w+)\s*=\s*"([^"]+)"', re.M)


def wire_input_types(root: Path, rel: str) -> dict:
    """InputType* constants: the wire `type` on a flow input. Returns {goIdent: wire}."""
    path = root / rel
    text = _read(path)
    out = {}
    for m in CONST_RE.finditer(text):
        ident, value = m.group(1), m.group(2)
        if ident.startswith("InputType"):
            out[ident] = value
    return out


def input_capabilities(root: Path, rel: str) -> list:
    path = root / rel
    text = _read(path)
    caps = []
    for m in CONST_RE.finditer(text):
        ident, value = m.group(1), m.group(2)
        if not ident.startswith("InputType"):
            continue
        caps.append(
            Capability(
                axis="input",
                key=value,
                name=value,
                wire=value,
                origin=f"{_rel(root, path)}:{_lineno(text, m.start())}",
                group="Wire input types",
                notes="An SDK that cannot render this input type cannot complete a flow that uses it.",
            )
        )
    return sorted(caps, key=lambda c: c.key)


# ------------------------------------------------------------------------ element types

ELEMENT_BLOCK_RE = re.compile(r"export const ElementTypes\s*=\s*\{(.*?)\}\s*as const", re.S)
ELEMENT_ROW_RE = re.compile(r"^\s*(\w+)\s*:\s*'([A-Z][A-Z0-9_]*)'", re.M)

# Element types that are authoring or layout concerns and never arrive as a component an
# SDK has to render on its own.
ELEMENT_INTERNAL = {"DYNAMIC_INPUT_PLACEHOLDER", "CUSTOM"}


def element_capabilities(root: Path, rel: str) -> list:
    """The console's flow element palette: everything a flow author can place on a step."""
    path = root / rel
    if not path.exists():
        return []
    text = _read(path)
    block = ELEMENT_BLOCK_RE.search(text)
    if not block:
        return []
    base = block.start(1)
    caps = []
    for m in ELEMENT_ROW_RE.finditer(block.group(1)):
        wire = m.group(2)
        caps.append(
            Capability(
                axis="element",
                key=wire,
                name=wire,
                wire=wire,
                origin=f"{_rel(root, path)}:{_lineno(text, base + m.start())}",
                group="Flow element palette",
                client_facing=wire not in ELEMENT_INTERNAL,
                notes="Placeable in a flow from the console, so any SDK may be handed one.",
            )
        )
    return sorted(caps, key=lambda c: c.key)


# ---------------------------------------------------------------------------- executors

EXEC_NAME_RE = re.compile(r"^\s*(ExecutorName\w+)\s*=\s*\"([^\"]+)\"", re.M)
REGISTER_RE = re.compile(r"RegisterExecutor\(\s*(ExecutorName\w+)\s*,\s*(\w+)\(")
CTOR_RE = re.compile(r"^func\s+(\w+)\s*\(", re.M)
STRUCT_RE = re.compile(r"^type\s+(\w+)\s+struct\s*\{(.*?)^\}", re.M | re.S)
# Only the executor's own prompt list counts. A `prerequisites` list is context the
# engine supplies from earlier steps, never something the client is asked for.
INPUT_LIST_RE = re.compile(r"(\w+)\s*:?=\s*\[\]providers\.Input\{(.*?)\n\t\}", re.S)
PREREQUISITE_VARS = {"prerequisites", "prereqs", "requiredContext"}
INPUT_ITEM_RE = re.compile(r"Identifier:\s*([^,\n]+),\s*\n\s*Type:\s*([^,\n]+),")

CLIENT_FACING_STATUS = ("ExecUserInputRequired", "ExecExternalRedirection")

# The Go identifier, as it reaches the client on the wire.
WIRE_STATUS = {
    "ExecUserInputRequired": "USER_INPUT_REQUIRED",
    "ExecExternalRedirection": "EXTERNAL_REDIRECTION",
}


def _go_files(d: Path) -> list:
    return [p for p in sorted(d.glob("*.go")) if not p.name.endswith("_test.go")]


def _resolve_consts(text: str) -> dict:
    """Local `ident = "value"` constants, so an input Identifier resolves to its wire name."""
    return {m.group(1): m.group(2) for m in CONST_RE.finditer(text)}


def executor_capabilities(root: Path, exec_dir_rel: str, consts_rel: str, wire_types: dict) -> list:
    exec_dir = root / exec_dir_rel
    consts_path = root / consts_rel
    consts_text = _read(consts_path)

    # ExecutorNameFoo -> "FooExecutor"
    names = {m.group(1): m.group(2) for m in EXEC_NAME_RE.finditer(consts_text)}
    name_lines = {m.group(1): _lineno(consts_text, m.start()) for m in EXEC_NAME_RE.finditer(consts_text)}

    files = _go_files(exec_dir)
    texts = {p: _read(p) for p in files}

    # Input identifiers are declared as constants, and not always in the file that uses
    # them, so the lookup table is built across the whole package.
    package_consts = {}
    for _t in texts.values():
        package_consts.update(_resolve_consts(_t))

    # constructor name -> defining file
    ctor_file = {}
    for p, t in texts.items():
        for m in CTOR_RE.finditer(t):
            ctor_file.setdefault(m.group(1), p)

    # struct name -> (file, embedded type names)
    struct_file, struct_embeds = {}, {}
    for p, t in texts.items():
        for m in STRUCT_RE.finditer(t):
            sname, body = m.group(1), m.group(2)
            struct_file[sname] = p
            embeds = []
            for line in body.splitlines():
                line = line.strip()
                # An embedded field is a bare type name with no field name before it.
                if re.fullmatch(r"[A-Za-z_]\w*", line):
                    embeds.append(line)
            struct_embeds[sname] = embeds

    # Which const each registration uses, and the constructor behind it.
    reg_ctor = {}
    for p, t in texts.items():
        for m in REGISTER_RE.finditer(t):
            reg_ctor[m.group(1)] = m.group(2)

    def impl_file(const_ident):
        ctor = reg_ctor.get(const_ident)
        return ctor_file.get(ctor) if ctor else None

    def emits_client_status(path, seen=None):
        """A file is client-facing if it emits a client status, or embeds something that does."""
        if path is None:
            return False, None
        seen = seen or set()
        if path in seen:
            return False, None
        seen.add(path)
        t = texts.get(path, "")
        for status in CLIENT_FACING_STATUS:
            if status in t:
                return True, status
        # Follow embedded interfaces: `oAuthExecutorInterface` -> struct `oAuthExecutor`.
        for sname, embeds in struct_embeds.items():
            if struct_file.get(sname) != path:
                continue
            for emb in embeds:
                target = re.sub(r"Interface$", "", emb)
                cand = struct_file.get(target) or struct_file.get(target[0].lower() + target[1:])
                ok, status = emits_client_status(cand, seen)
                if ok:
                    return True, status
        return False, None

    caps = []
    for const_ident, wire_name in sorted(names.items(), key=lambda kv: kv[1]):
        path = impl_file(const_ident)
        facing, status = emits_client_status(path)
        inputs = []
        if path is not None:
            t = texts[path]
            local = dict(package_consts)
            local.update(_resolve_consts(t))
            for block in INPUT_LIST_RE.finditer(t):
                if block.group(1) in PREREQUISITE_VARS:
                    continue
                for item in INPUT_ITEM_RE.finditer(block.group(2)):
                    ident_expr = item.group(1).strip()
                    type_expr = item.group(2).strip()
                    if ident_expr.startswith('"'):
                        ident = ident_expr.strip('"')
                    elif ident_expr in local:
                        ident = local[ident_expr]
                    else:
                        continue  # unresolved constant: not a searchable wire name
                    if type_expr.startswith("providers."):
                        type_expr = type_expr.split(".", 1)[1]
                    wire_type = wire_types.get(type_expr, type_expr.strip('"'))
                    inputs.append((ident, wire_type))

        caps.append(
            Capability(
                axis="executor",
                key=wire_name,
                name=wire_name,
                wire=None,  # SDKs never name an executor; support is inferred from its inputs
                origin=f"{_rel(root, consts_path)}:{name_lines[const_ident]}",
                group="Client-facing" if facing else "Server-internal",
                client_facing=facing,
                inputs=sorted(set(inputs)),
                notes=(
                    f"Emits {WIRE_STATUS.get(status, status)} to the client."
                    if facing
                    else "Never prompts the client; no SDK support required."
                ),
            )
        )
    return caps


# --------------------------------------------------------------------------------- spec

SECTION_RE = r"\n### {0}\n(.*?)(?=\n### |\n## |\Z)"
GROUP_RE = re.compile(r"^\*\*(.+?)\*\*\s*$", re.M)
ROW_RE = re.compile(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|(.*)$", re.M)
BACKTICK_RE = re.compile(r"`([^`]+)`")


def _section(text: str, heading: str) -> tuple:
    m = re.search(SECTION_RE.format(re.escape(heading)), text, re.S)
    if not m:
        return "", 0
    return m.group(1), m.start(1)


def _groups(section: str) -> list:
    """Split a section into (group name, body) using its **Bold** subheadings."""
    marks = list(GROUP_RE.finditer(section))
    if not marks:
        return [("", section, 0)]
    out = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(section)
        out.append((m.group(1), section[m.end():end], m.end()))
    return out


def surface_capabilities(root: Path, spec_rel: str) -> list:
    path = root / spec_rel
    text = _read(path)
    section, base = _section(text, "Client surface")
    caps = []
    for group, body, offset in _groups(section):
        for m in ROW_RE.finditer(body):
            first, second = m.group(1), m.group(2)
            if first.startswith("---") or first.lower() in ("operation", "key", "type"):
                continue
            ops = BACKTICK_RE.findall(first)
            if not ops:
                continue
            line = _lineno(text, base + offset + m.start())
            for op in ops:
                caps.append(
                    Capability(
                        axis="surface",
                        key=op,
                        name=op,
                        origin=f"{_rel(root, path)}:{line}",
                        group=group or "Operations",
                        required=True,
                        notes=second.strip(),
                    )
                )
    return caps


def config_capabilities(root: Path, spec_rel: str) -> list:
    path = root / spec_rel
    text = _read(path)
    section, base = _section(text, "Configuration")
    caps = []
    for group, body, offset in _groups(section):
        for m in ROW_RE.finditer(body):
            first, rest = m.group(1), m.group(3)
            if first.startswith("---") or first.lower() == "key":
                continue
            keys = BACKTICK_RE.findall(first)
            if not keys:
                continue
            cols = [c.strip() for c in (m.group(2) + "|" + rest).split("|")]
            required = len(cols) > 1 and cols[1].lower() in ("yes", "conditional")
            line = _lineno(text, base + offset + m.start())
            caps.append(
                Capability(
                    axis="config",
                    key=keys[0],
                    name=keys[0],
                    origin=f"{_rel(root, path)}:{line}",
                    group=group or "Keys",
                    required=required,
                    notes=(cols[-1] if cols else "").strip(),
                )
            )
    return caps


def discover(root: Path, sources: dict) -> list:
    wire_types = wire_input_types(root, sources["wire_consts"])
    caps = []
    caps += executor_capabilities(root, sources["executor_dir"], sources["executor_consts"], wire_types)
    caps += input_capabilities(root, sources["wire_consts"])
    caps += element_capabilities(root, sources["element_types"])
    caps += surface_capabilities(root, sources["spec"])
    caps += config_capabilities(root, sources["spec"])
    return caps


# ------------------------------------------------------- operations beyond the spec

def extra_operation_capabilities(indexes, surface_caps, overrides) -> list:
    """Operations an SDK exposes that the specification does not name.

    The specification says so itself: operations in this position are "the usual origin of
    a parity gap". One SDK grows a method, the others do not, and nothing notices. So the
    union of every SDK's client surface is taken, the specified operations are removed,
    and what remains is scored like anything else - which turns an undocumented extra into
    a visible row instead of a private convenience.
    """
    from .sdk import norm

    specified = set()
    for cap in surface_caps:
        specified.add(norm(cap.key))
        for alias in ((overrides.get(cap.uid) or {}).get("aliases") or []):
            specified.add(norm(alias))

    # normalized name -> (display name, {sdk id: "file:line"})
    seen = {}
    for sid, index in indexes.items():
        for n, where in index.methods().items():
            if n in specified:
                continue
            seen.setdefault(n, [None, {}])
            seen[n][1][sid] = where

    caps = []
    for n, (_, places) in sorted(seen.items()):
        # An operation only one SDK has is the interesting case, but all are carried:
        # a name three SDKs share and a fourth lacks is the same kind of gap.
        display = next((getattr(indexes[sid], "spellings", {}).get(n) for sid in places
                         if getattr(indexes[sid], "spellings", {}).get(n)), n)
        origin = ", ".join(f"{sid}" for sid in sorted(places))
        caps.append(
            Capability(
                axis="extra",
                key=n,
                name=display,
                origin=f"defined in: {origin}",
                group="Present in some SDKs only" if len(places) < len(indexes) else "Present in every SDK",
                required=False,
                notes=("Not named in the specification. Either it belongs in the spec and in "
                       "every SDK, or it should not be public."),
            )
        )
        caps[-1].places = places
    return caps
