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
/* expandable detail */
tr.row{cursor:pointer}
tr.row:focus-visible{outline:2px solid var(--ink);outline-offset:-2px}
td.cap .tw{display:inline-flex;align-items:center;gap:7px}
.caret{color:var(--muted);font-size:10px;transition:transform .12s ease;display:inline-block}
tr.row[aria-expanded="true"] .caret{transform:rotate(90deg)}
td.tested{text-align:center;width:66px;color:var(--ink2);font-variant-numeric:tabular-nums;
white-space:nowrap}
tr.detail>td{background:var(--plane);padding:0}
.dwrap{padding:14px 16px;border-left:3px solid var(--rule)}
.dmeta{color:var(--ink2);margin:0 0 12px;max-width:80ch}
.dmeta code{font-size:11px;color:var(--muted)}
.psuite{display:block;margin-top:9px;padding-top:9px;border-top:1px solid var(--grid);font-size:12px}
.psuite b{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--ink2)}
.psuite ul{list-style:none;margin:5px 0 0;padding:0}
.psuite li{color:var(--muted);font-size:11px;font-variant-numeric:tabular-nums;word-break:break-all}
.dgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px}
.dcard{background:var(--surface);border:1px solid var(--ring);border-radius:9px;padding:12px}
.dcard h4{margin:0 0 8px;font-size:13px;display:flex;align-items:center;
justify-content:space-between;gap:8px}
.dcard .why{color:var(--ink2);font-size:12px;margin:0 0 9px}
ul.parts{list-style:none;margin:0 0 9px;padding:0;font-size:12px}
ul.parts li{display:flex;gap:7px;align-items:baseline;padding:2px 0;
border-bottom:1px solid var(--grid)}
ul.parts li:last-child{border-bottom:0}
ul.parts .m{font-weight:700;width:11px;flex:none}
ul.parts .n{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px}
ul.parts .k{color:var(--muted);font-size:11px;margin-left:auto;white-space:nowrap}
ul.parts .ev{display:block;color:var(--muted);font-size:11px;
font-variant-numeric:tabular-nums;word-break:break-all}
.tsec{border-top:1px solid var(--grid);padding-top:8px;font-size:12px}
.tsec b{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--ink2)}
.tsec ul{list-style:none;margin:5px 0 0;padding:0}
.tsec li{color:var(--muted);font-size:11px;font-variant-numeric:tabular-nums;
word-break:break-all;padding:1px 0}
.tsec .none{color:var(--crit)}
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
      const d=document.getElementById(tr.dataset.detail);
      if(d && !vis){ d.hidden=true; tr.setAttribute('aria-expanded','false'); }
    });
    // A group heading is only meaningful while a row under it survives the filter.
    sec.querySelectorAll('tbody tr.grp').forEach(h=>{
      let n=h.nextElementSibling, any=false;
      while(n && !n.classList.contains('grp')){
        if(!n.hidden && n.classList.contains('row')) any=true;
        n=n.nextElementSibling;
      }
      h.hidden=!any;
    });
    sec.hidden = shown===0;
    const e=sec.querySelector('.empty'); if(e) e.hidden = shown!==0;
  });
}
[q,ax,gapsOnly].forEach(el=>el.addEventListener('input',apply));

// Rows expand in place rather than opening a panel, so several can be compared at once
// and a filtered view keeps its shape.
function toggle(tr){
  const d=document.getElementById(tr.dataset.detail);
  if(!d) return;
  const open=tr.getAttribute('aria-expanded')==='true';
  tr.setAttribute('aria-expanded', open?'false':'true');
  d.hidden=open;
}
document.querySelectorAll('tr.row').forEach(tr=>{
  tr.addEventListener('click',e=>{ if(!e.target.closest('a')) toggle(tr); });
  tr.addEventListener('keydown',e=>{
    if(e.key==='Enter'||e.key===' '){ e.preventDefault(); toggle(tr); }
  });
});
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


def _parts_list(finding):
    if not finding.parts:
        return '<p class="why">Nothing to check against; see the reason above.</p>'
    head = ("Needs all of:" if finding.match_mode == "all" and len(finding.parts) > 1
            else "Needs any one of:" if finding.match_mode == "any" else "Needs:")
    items = []
    for part in finding.parts:
        mark = "\u2713" if part.found else "\u2715"
        color = STATUS[SUPPORTED]["color"] if part.found else STATUS[MISSING]["color"]
        ev = ("".join(f'<span class="ev">{_esc(e)}</span>' for e in part.evidence[:2])
              if part.found else '<span class="ev">not found</span>')
        items.append(
            f'<li><span class="m" style="color:{color}" aria-hidden="true">{mark}</span>'
            f'<span><span class="n">{_esc(part.name)}</span>{ev}</span>'
            f'<span class="k">{_esc(part.kind)}</span></li>'
        )
    return (f'<p class="why" style="margin-bottom:5px"><b style="font-size:11px;'
            f'text-transform:uppercase;letter-spacing:.06em">{head}</b></p>'
            f'<ul class="parts">{"".join(items)}</ul>')


def _tests_block(finding):
    if not finding.tests:
        return ('<div class="tsec"><b>End-to-end</b>'
                '<ul><li class="none">No test in this SDK\'s suite references it.</li></ul></div>')
    seen, items = set(), []
    for term, where in finding.tests:
        if where in seen:
            continue
        seen.add(where)
        items.append(f'<li>{_esc(where)} <span style="opacity:.75">via {_esc(term)}</span></li>')
    return (f'<div class="tsec"><b>End-to-end &middot; {len(seen)} reference'
            f'{"s" if len(seen) != 1 else ""}</b><ul>{"".join(items[:6])}</ul></div>')


def _detail(cap, row, sdks, detail_id, cols):
    meta = [f'Discovered at <code>{_esc(cap.origin)}</code>.']
    if cap.notes:
        meta.append(_esc(cap.notes))
    if cap.inputs:
        meta.append("Declared inputs: " + ", ".join(
            f'<code>{_esc(i)}</code> ({_esc(t)})' for i, t in cap.inputs))
    prod = getattr(row, "product_tests", [])
    if prod:
        seen, items = set(), []
        for term, where in prod:
            if where in seen:
                continue
            seen.add(where)
            items.append(f'<li>{_esc(where)} <span style="opacity:.75">via {_esc(term)}</span></li>')
        covered = any(f.tests for f in row.findings.values())
        note = ("" if covered else
                ' <span style="color:var(--crit)">Exercised by the server\'s suites and by '
                'no SDK suite.</span>')
        meta.append(f'<span class="psuite"><b>Product suites &middot; {len(seen)} reference'
                    f'{"s" if len(seen) != 1 else ""}</b>{note}<ul>{"".join(items[:6])}</ul></span>')

    cards = []
    for sdk in sdks:
        f = row.findings[sdk["id"]]
        m = STATUS[f.status]
        cards.append(
            f'<div class="dcard"><h4>{_esc(sdk["label"])}'
            f'<span class="pill" style="color:{m["color"]};background:{m["color"]}18;'
            f'border-color:{m["color"]}40"><i aria-hidden="true">{m["glyph"]}</i>'
            f'<span>{m["label"]}</span></span></h4>'
            + (f'<p class="why">{_esc(f.reason)}</p>' if f.reason else "")
            + _parts_list(f) + _tests_block(f) + '</div>'
        )
    return (f'<tr class="detail" id="{detail_id}" hidden><td colspan="{cols}">'
            f'<div class="dwrap"><p class="dmeta">{" ".join(meta)}</p>'
            f'<div class="dgrid">{"".join(cards)}</div></div></td></tr>')


def _matrix(axis, title, rows, sdks):
    if not rows:
        return ""
    head = "".join(f"<th>{_esc(s['label'])}</th>" for s in sdks) + "<th>E2E</th>"
    body, last_group = [], None
    for r in sorted(rows, key=lambda r: (r.capability.group, not r.is_gap, r.capability.name)):
        cap = r.capability
        if cap.group != last_group:
            last_group = cap.group
            body.append(f'<tr class="grp"><td colspan="{len(sdks)+2}">{_esc(cap.group)}</td></tr>')
        detail = cap.notes
        if cap.inputs:
            detail += "  Inputs: " + ", ".join(f"{i} ({t})" for i, t in cap.inputs)
        cells = "".join(_cell(r.findings[s["id"]]) for s in sdks)
        detail_id = f"d-{axis}-{abs(hash(cap.uid)) % 10**9}"
        tested = sum(1 for s in sdks if r.findings[s["id"]].tests)
        scored_n = sum(1 for s in sdks if r.findings[s["id"]].status != NOT_APPLICABLE)
        tint = (STATUS[SUPPORTED]["color"] if tested and tested >= scored_n
                else STATUS[PARTIAL]["color"] if tested
                else STATUS[MISSING]["color"] if scored_n else "var(--muted)")
        e2e = (f'<td class="tested" style="color:{tint}" '
               f'title="End-to-end suites referencing this capability">'
               f'{tested}/{len(sdks)}</td>')
        body.append(
            f'<tr class="row" tabindex="0" role="button" aria-expanded="false" '
            f'aria-controls="{detail_id}" data-detail="{detail_id}" '
            f'data-name="{_esc(cap.name.lower())}" data-gap="{1 if r.is_gap else 0}">'
            f'<td class="cap" title="{_esc(detail)}">'
            f'<span class="tw"><span class="caret" aria-hidden="true">&#9654;</span>'
            f'<b>{_esc(cap.name)}</b></span>'
            f'<span class="origin">{_esc(cap.origin)}</span></td>{cells}{e2e}</tr>'
        )
        body.append(_detail(cap, r, sdks, detail_id, len(sdks) + 2))
    legend = "".join(
        f'<span><i class="dot" style="background:{m["color"]}"></i>'
        f'<i aria-hidden="true" style="color:{m["color"]};font-weight:700">{m["glyph"]}</i>'
        f'{m["label"]}</span>'
        for m in STATUS.values()
    )
    legend += ('<span style="margin-left:auto;color:var(--muted)">'
               'E2E: SDK suites referencing the capability &middot; '
               'select a row for the evidence behind every cell</span>')
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
