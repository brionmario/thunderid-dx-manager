"""Renders the parity matrix as one self-contained HTML page.

The page is a table, deliberately: the data is categorical status across five axes and
four SDKs, and a table is the form that carries it without inventing a chart. Status is
never colour alone - every cell pairs a glyph with the colour and names the status in its
tooltip and its accessible label.
"""

from __future__ import annotations

import html
import json
from collections import OrderedDict

from .model import (AXES, MISSING, NOT_APPLICABLE, PARTIAL, SUPPORTED, UNDETERMINED)

# Status palette, fixed and never themed. Glyph carries the meaning when colour cannot.
STATUS = OrderedDict([
    (SUPPORTED,      {"glyph": "✓", "label": "Supported",  "color": "#0ca30c"}),
    (PARTIAL,        {"glyph": "◐", "label": "Partial",    "color": "#fab219"}),
    (MISSING,        {"glyph": "✕", "label": "Missing",    "color": "#d03b3b"}),
    (UNDETERMINED,   {"glyph": "?",      "label": "Unverified", "color": "#ec835a"}),
    (NOT_APPLICABLE, {"glyph": "–", "label": "Not applicable", "color": "#898781"}),
])

CSS = """
:root{color-scheme:light;--surface:#fcfcfb;--plane:#f9f9f7;--ink:#0b0b0b;--ink2:#52514e;
--muted:#898781;--grid:#e1e0d9;--rule:#c3c2b7;--ring:rgba(11,11,11,.10);
--good:#0ca30c;--warn:#fab219;--serious:#ec835a;--crit:#d03b3b;}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;
--surface:#1a1a19;--plane:#0d0d0d;--ink:#fff;--ink2:#c3c2b7;--muted:#898781;
--grid:#2c2c2a;--rule:#383835;--ring:rgba(255,255,255,.10);}}
:root[data-theme="dark"]{color-scheme:dark;--surface:#1a1a19;--plane:#0d0d0d;--ink:#fff;
--ink2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--rule:#383835;--ring:rgba(255,255,255,.10);}
*{box-sizing:border-box}
body{margin:0;background:var(--plane);color:var(--ink);
font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;
padding:0 16px env(safe-area-inset-bottom,0px);}
.wrap{max-width:1180px;margin:0 auto;padding-block:28px}
h1{font-size:22px;margin:0 0 4px;letter-spacing:-.01em}
h2{font-size:15px;margin:0;letter-spacing:-.005em}
.sub{color:var(--ink2);margin:0 0 20px;max-width:70ch}
.card{background:var(--surface);border:1px solid var(--ring);border-radius:10px;
margin-bottom:16px;overflow:hidden}
.card>header{padding:12px 16px;border-bottom:1px solid var(--grid);
display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
.card>header .count{color:var(--muted);font-size:12px;font-variant-numeric:tabular-nums}
.pad{padding:14px 16px}
/* stat tiles */
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}
.tile{background:var(--surface);border:1px solid var(--ring);border-radius:10px;padding:14px 16px}
.tile .name{font-size:12px;color:var(--ink2);text-transform:uppercase;letter-spacing:.06em}
.tile .num{font-size:30px;line-height:1.15;margin:4px 0 2px}
.tile .meta{font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums}
.bar{height:8px;border-radius:4px;background:var(--grid);overflow:hidden;display:flex;margin:10px 0 8px}
.bar span{height:100%}
.bar span:first-child{border-radius:4px 0 0 4px}
.bar span:last-child{border-radius:0 4px 4px 0}
/* controls */
.controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:0 0 16px}
input[type=search],select{font:inherit;padding:7px 10px;border-radius:8px;
border:1px solid var(--rule);background:var(--surface);color:var(--ink);min-width:0}
input[type=search]{flex:1 1 220px}
label.chk{display:inline-flex;gap:6px;align-items:center;color:var(--ink2);
border:1px solid var(--rule);border-radius:8px;padding:7px 10px;background:var(--surface);cursor:pointer}
/* matrix */
.scroll{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--grid);vertical-align:top}
thead th{position:sticky;top:0;background:var(--surface);z-index:2;
font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--ink2);
border-bottom:1px solid var(--rule);white-space:nowrap}
tbody tr:hover{background:var(--plane)}
td.cap{min-width:230px}
td.cap b{font-weight:600}
td.cap .origin{display:block;color:var(--muted);font-size:11px;margin-top:1px;
font-variant-numeric:tabular-nums}
td.st{text-align:center;width:104px}
.pill{display:inline-flex;align-items:center;gap:5px;border-radius:999px;
padding:2px 9px;font-size:12px;border:1px solid transparent;cursor:help;white-space:nowrap}
.pill i{font-style:normal;font-weight:700}
.grp{background:var(--plane);font-size:11px;text-transform:uppercase;
letter-spacing:.06em;color:var(--ink2)}
.grp td{padding:6px 10px;border-bottom:1px solid var(--grid)}
/* legend & alerts */
.legend{display:flex;gap:14px;flex-wrap:wrap;color:var(--ink2);font-size:12px;
padding:10px 16px;border-top:1px solid var(--grid)}
.legend span{display:inline-flex;align-items:center;gap:6px}
.dot{width:10px;height:10px;border-radius:3px;display:inline-block}
ul.alert{margin:0;padding-left:20px}
ul.alert li{margin:3px 0}
ul.alert code{font-size:12px}
.empty{color:var(--muted);padding:14px 16px}
footer{color:var(--muted);font-size:12px;margin:22px 0 8px;line-height:1.7}
footer code{font-size:11px}
a{color:inherit}
@media (max-width:640px){td.cap{min-width:150px}td.st{width:56px}
.pill span{display:none}.num{font-size:26px}}
"""

JS = """
const q=document.getElementById('q'),ax=document.getElementById('ax'),
gapsOnly=document.getElementById('gapsOnly');
function apply(){
  const term=q.value.trim().toLowerCase(), axis=ax.value, only=gapsOnly.checked;
  document.querySelectorAll('section[data-axis]').forEach(sec=>{
    let shown=0;
    sec.querySelectorAll('tbody tr[data-name]').forEach(tr=>{
      const okAxis = axis==='all' || sec.dataset.axis===axis;
      const okTerm = !term || tr.dataset.name.includes(term);
      const okGap  = !only || tr.dataset.gap==='1';
      const vis = okAxis && okTerm && okGap;
      tr.hidden=!vis; if(vis) shown++;
    });
    // A group heading is only meaningful while a row under it survives the filter.
    sec.querySelectorAll('tbody tr.grp').forEach(h=>{
      let n=h.nextElementSibling, any=false;
      while(n && !n.classList.contains('grp')){ if(!n.hidden) any=true; n=n.nextElementSibling; }
      h.hidden=!any;
    });
    sec.hidden = shown===0;
    const e=sec.querySelector('.empty'); if(e) e.hidden = shown!==0;
  });
}
[q,ax,gapsOnly].forEach(el=>el.addEventListener('input',apply));
apply();
"""


def _esc(s) -> str:
    return html.escape(str(s or ""), quote=True)


def _tile(sdk, rows):
    scored = [r for r in rows if r.findings[sdk["id"]].status != NOT_APPLICABLE]
    counts = {k: 0 for k in STATUS}
    for r in scored:
        counts[r.findings[sdk["id"]].status] += 1
    total = len(scored) or 1
    pct = 100 * counts[SUPPORTED] / total
    seg = "".join(
        f'<span style="width:{100*counts[k]/total:.3f}%;background:{STATUS[k]["color"]}"></span>'
        for k in (SUPPORTED, PARTIAL, UNDETERMINED, MISSING) if counts[k]
    )
    return f"""<div class="tile">
  <div class="name">{_esc(sdk['label'])}</div>
  <div class="num">{pct:.0f}%</div>
  <div class="bar">{seg}</div>
  <div class="meta">{counts[SUPPORTED]} supported &middot; {counts[PARTIAL]} partial &middot;
    {counts[MISSING]} missing &middot; {counts[UNDETERMINED]} unverified</div>
  <div class="meta" style="margin-top:6px">{_esc(sdk['commit'])} on {_esc(sdk['branch'])}</div>
</div>"""


def _cell(finding):
    meta = STATUS[finding.status]
    bits = [meta["label"]]
    if finding.reason:
        bits.append(finding.reason)
    if finding.evidence:
        bits.append("Evidence: " + ", ".join(finding.evidence[:4]))
    tip = _esc(" · ".join(bits))
    tint = "18" if finding.status != NOT_APPLICABLE else "10"
    return (f'<td class="st"><span class="pill" title="{tip}" aria-label="{tip}" '
            f'style="color:{meta["color"]};background:{meta["color"]}{tint};'
            f'border-color:{meta["color"]}40">'
            f'<i aria-hidden="true">{meta["glyph"]}</i><span>{meta["label"]}</span></span></td>')


def _matrix(axis, title, rows, sdks):
    if not rows:
        return ""
    head = "".join(f"<th>{_esc(s['label'])}</th>" for s in sdks)
    body, last_group = [], None
    for r in sorted(rows, key=lambda r: (r.capability.group, not r.is_gap, r.capability.name)):
        cap = r.capability
        if cap.group != last_group:
            last_group = cap.group
            body.append(f'<tr class="grp"><td colspan="{len(sdks)+1}">{_esc(cap.group)}</td></tr>')
        detail = cap.notes
        if cap.inputs:
            detail += "  Inputs: " + ", ".join(f"{i} ({t})" for i, t in cap.inputs)
        cells = "".join(_cell(r.findings[s["id"]]) for s in sdks)
        body.append(
            f'<tr data-name="{_esc(cap.name.lower())}" data-gap="{1 if r.is_gap else 0}">'
            f'<td class="cap" title="{_esc(detail)}"><b>{_esc(cap.name)}</b>'
            f'<span class="origin">{_esc(cap.origin)}</span></td>{cells}</tr>'
        )
    legend = "".join(
        f'<span><i class="dot" style="background:{m["color"]}"></i>'
        f'<i aria-hidden="true" style="color:{m["color"]};font-weight:700">{m["glyph"]}</i>'
        f'{m["label"]}</span>'
        for m in STATUS.values()
    )
    return f"""<section class="card" data-axis="{axis}">
  <header><h2>{_esc(title)}</h2><span class="count">{len(rows)} capabilities</span></header>
  <div class="scroll"><table>
    <thead><tr><th>Capability</th>{head}</tr></thead>
    <tbody>{''.join(body)}</tbody>
  </table></div>
  <p class="empty" hidden>Nothing matches the current filter.</p>
  <div class="legend">{legend}</div>
</section>"""


def _alerts(rows, stale):
    items = []

    orphans = [r for r in rows if getattr(r, "scored", True) and r.is_total_gap]
    if orphans:
        items.append((
            "Supported by no SDK",
            "The product can emit these and not one SDK handles them. A flow that uses one "
            "breaks everywhere.",
            [f"<code>{_esc(r.capability.name)}</code> "
             f"<span style='color:var(--muted)'>{_esc(r.capability.origin)}</span>"
             for r in orphans],
        ))

    unknown = [r for r in rows
               if getattr(r, "scored", True)
               and all(f.status == UNDETERMINED for f in r.findings.values())]
    if unknown:
        items.append((
            "No detector yet",
            "Discovered in the product, but nothing here can prove whether an SDK handles it. "
            "Add a detector in catalogue/overrides.yaml to turn each into a real verdict.",
            [f"<code>{_esc(r.capability.name)}</code>" for r in unknown],
        ))

    if stale:
        items.append((
            "Stale overrides",
            "These name a capability that no longer exists upstream. Remove them, or find out "
            "what replaced it.",
            [f"<code>{_esc(k)}</code>" for k in stale],
        ))

    if not items:
        return ""
    blocks = "".join(
        f'<div class="pad"><h2>{_esc(t)}</h2><p class="sub" style="margin:4px 0 8px">{_esc(d)}</p>'
        f'<ul class="alert">{"".join(f"<li>{x}</li>" for x in xs)}</ul></div>'
        for t, d, xs in items
    )
    return f'<section class="card" style="border-color:#d03b3b40">{blocks}</section>'


def render(result) -> str:
    rows, sdks = result["rows"], result["sdks"]
    scored = [r for r in rows if getattr(r, "scored", True)]

    tiles = "".join(_tile(s, scored) for s in sdks)
    axis_opts = "".join(f'<option value="{k}">{_esc(v)}</option>' for k, v in AXES.items())
    sections = "".join(
        _matrix(axis, title, [r for r in rows if r.capability.axis == axis], sdks)
        for axis, title in AXES.items()
    )
    prov = " &middot; ".join(
        f"{_esc(s['label'])} <code>{_esc(s['commit'])}</code>" for s in sdks)
    total_gaps = sum(1 for r in scored if r.is_gap)

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>ThunderID SDK Parity</title>
<style>{CSS}</style></head>
<body><div class="wrap">
<h1>ThunderID SDK parity</h1>
<p class="sub">Every capability the product can ask of an SDK, and whether each SDK answers.
Discovered from source on each run: executors and wire constants from the server, the element
palette from the console, the client surface and configuration keys from the SDK specification.
<b>{total_gaps}</b> of {len(scored)} capabilities are short in at least one SDK.</p>

<div class="tiles" style="margin-bottom:18px">{tiles}</div>

{_alerts(rows, result["stale_overrides"])}

<div class="controls">
  <input type="search" id="q" placeholder="Filter capabilities&hellip;" aria-label="Filter capabilities">
  <select id="ax" aria-label="Axis"><option value="all">All axes</option>{axis_opts}</select>
  <label class="chk"><input type="checkbox" id="gapsOnly"> Gaps only</label>
</div>

{sections}

<footer>
Product <code>{_esc(result['product']['commit'])}</code> on
<code>{_esc(result['product']['branch'])}</code> &middot; {prov}<br>
Generated {_esc(result['generated'])}. Each row cites the file and line it was discovered from;
hover a cell for the evidence behind it.
</footer>
</div>
<script>{JS}</script>
</body></html>"""
