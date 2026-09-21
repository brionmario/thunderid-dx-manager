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

# The ThunderID logo, from skills/assets/images/brand/logo.svg. Inlined so the report
# remains one self-contained file. The brand ships a light and an inverted variant whose
# geometry is identical and whose ink colour is the only difference, so that colour is a
# custom property here and the theme drives it, rather than shipping both files.
LOGO = """<svg class="mark" viewBox="0 0 1187 257" role="img" aria-label="ThunderID" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M286.26 92.5581V70.7585H391.069V92.5581H351.882V199.098H325.532V92.5581H286.26Z"
    fill="var(--logo-ink)" />
  <path
    d="M434.366 143.381V199.098H408.524V70.7585H433.837V126.836H431.761C434.281 118.807 438.115 112.578 443.263 108.193C448.41 103.807 455.04 101.604 463.195 101.604C469.846 101.604 475.672 103.045 480.628 105.947C485.585 108.85 489.461 113.002 492.215 118.446C494.969 123.891 496.346 130.352 496.346 137.873V199.12H470.418V142.364C470.418 136.39 468.872 131.708 465.822 128.319C462.75 124.929 458.493 123.234 453.028 123.234C449.405 123.234 446.186 124.018 443.347 125.607C440.509 127.196 438.285 129.463 436.717 132.45C435.129 135.437 434.345 139.081 434.345 143.381H434.366Z"
    fill="var(--logo-ink)" />
  <path
    d="M551.504 200.306C544.853 200.306 539.007 198.865 534.029 195.963C529.03 193.061 525.175 188.908 522.442 183.485C519.71 178.062 518.354 171.579 518.354 164.058V102.812H544.196V159.567C544.196 165.541 545.743 170.223 548.856 173.613C551.949 177.002 556.207 178.697 561.608 178.697C565.273 178.697 568.535 177.913 571.331 176.324C574.148 174.735 576.33 172.447 577.919 169.439C579.507 166.431 580.291 162.787 580.291 158.55V102.833H606.218V199.12H581.753L581.414 175.096H582.875C580.354 183.188 576.478 189.417 571.289 193.781C566.099 198.145 559.511 200.327 551.525 200.327L551.504 200.306Z"
    fill="var(--logo-ink)" />
  <path
    d="M653.984 143.381V199.098H628.142V102.812H652.523L652.946 126.836H651.4C653.921 118.807 657.755 112.578 662.902 108.193C668.049 103.807 674.679 101.604 682.834 101.604C689.486 101.604 695.311 103.045 700.268 105.947C705.224 108.85 709.079 113.002 711.812 118.446C714.544 123.87 715.9 130.352 715.9 137.873V199.12H690.058V142.364C690.058 136.39 688.511 131.708 685.461 128.319C682.389 124.929 678.132 123.234 672.667 123.234C669.045 123.234 665.825 124.018 662.987 125.607C660.148 127.196 657.924 129.463 656.356 132.45C654.768 135.437 653.984 139.081 653.984 143.381Z"
    fill="var(--logo-ink)" />
  <path
    d="M773.071 200.751C765.721 200.751 759.07 198.844 753.138 195.031C747.186 191.217 742.505 185.625 739.052 178.231C735.599 170.859 733.884 161.812 733.884 151.135C733.884 140.458 735.663 131.009 739.222 123.658C742.78 116.307 747.525 110.799 753.435 107.112C759.345 103.447 765.869 101.604 772.986 101.604C778.43 101.604 782.984 102.515 786.585 104.358C790.208 106.201 793.131 108.468 795.376 111.159C797.621 113.849 799.273 116.476 800.375 118.997H801.243V70.7585H827.086V199.098H801.688V183.676H800.396C799.252 186.26 797.537 188.866 795.27 191.472C793.004 194.077 790.059 196.281 786.437 198.06C782.815 199.84 778.366 200.73 773.092 200.73L773.071 200.751ZM781.078 179.989C785.441 179.989 789.17 178.782 792.283 176.367C795.376 173.952 797.748 170.583 799.337 166.24C800.947 161.897 801.752 156.834 801.752 151.029C801.752 145.224 800.968 140.098 799.379 135.818C797.791 131.539 795.461 128.213 792.368 125.819C789.275 123.446 785.505 122.239 781.078 122.239C776.651 122.239 772.732 123.467 769.661 125.946C766.589 128.425 764.28 131.793 762.734 136.115C761.188 140.415 760.404 145.394 760.404 151.008C760.404 156.622 761.188 161.622 762.776 165.986C764.365 170.35 766.674 173.761 769.745 176.24C772.817 178.718 776.587 179.947 781.078 179.947V179.989Z"
    fill="var(--logo-ink)" />
  <path
    d="M892.603 201.005C882.795 201.005 874.322 198.992 867.205 194.967C860.088 190.942 854.623 185.243 850.789 177.828C846.976 170.414 845.07 161.643 845.07 151.474C845.07 141.305 846.955 132.852 850.746 125.374C854.538 117.917 859.897 112.091 866.845 107.896C873.793 103.701 881.948 101.604 891.311 101.604C897.623 101.604 903.511 102.6 908.955 104.612C914.399 106.625 919.208 109.655 923.338 113.701C927.469 117.747 930.71 122.811 933.018 128.912C935.348 134.992 936.513 142.174 936.513 150.436V157.681H855.64V141.496H923.847L911.794 145.796C911.794 140.797 911.031 136.454 909.506 132.746C907.981 129.039 905.715 126.179 902.707 124.124C899.699 122.09 895.971 121.073 891.544 121.073C887.116 121.073 883.261 122.111 880.126 124.166C876.991 126.243 874.619 129.039 873.03 132.556C871.42 136.094 870.615 140.119 870.615 144.652V156.114C870.615 161.685 871.548 166.367 873.412 170.159C875.276 173.952 877.881 176.79 881.249 178.676C884.617 180.561 888.536 181.515 893.005 181.515C896.055 181.515 898.809 181.091 901.266 180.222C903.744 179.354 905.841 178.083 907.6 176.388C909.358 174.693 910.692 172.617 911.603 170.138L935.031 174.524C933.485 179.799 930.773 184.438 926.939 188.442C923.084 192.425 918.276 195.518 912.514 197.7C906.752 199.882 900.101 200.963 892.581 200.963L892.603 201.005Z"
    fill="var(--logo-ink)" />
  <path
    d="M954.18 199.098V102.812H979.153V119.612H980.191C981.971 113.637 984.936 109.125 989.109 106.095C993.282 103.066 998.048 101.519 1003.45 101.519C1004.76 101.519 1006.2 101.583 1007.75 101.731C1009.3 101.88 1010.65 102.091 1011.8 102.388V125.48C1010.65 125.077 1008.98 124.76 1006.8 124.527C1004.61 124.293 1002.54 124.188 1000.59 124.188C996.692 124.188 993.155 125.035 989.999 126.73C986.843 128.425 984.385 130.776 982.627 133.784C980.869 136.793 980.001 140.31 980.001 144.335V199.12H954.158L954.18 199.098Z"
    fill="var(--logo-ink)" />
  <path d="M1055.64 70.7797V199.12H1029.38V70.7797H1055.64Z" fill="var(--logo-ink)" />
  <path
    d="M1105.15 70.7797V199.12H1078.88V70.7797H1105.15ZM1124.02 199.098H1090.78V176.451H1122.73C1130.99 176.451 1137.94 174.99 1143.53 172.066C1149.12 169.143 1153.34 164.609 1156.15 158.465C1158.97 152.322 1160.37 144.462 1160.37 134.865C1160.37 125.268 1158.95 117.514 1156.11 111.392C1153.27 105.269 1149.08 100.757 1143.53 97.8332C1137.98 94.9096 1131.12 93.4479 1122.9 93.4479H1090.17V70.8009H1124.44C1137.3 70.8009 1148.38 73.3643 1157.64 78.5123C1166.89 83.6603 1174.05 90.9904 1179.03 100.566C1184.03 110.121 1186.53 121.561 1186.53 134.886C1186.53 148.212 1184.03 159.757 1179.03 169.333C1174.03 178.93 1166.87 186.281 1157.55 191.429C1148.21 196.577 1137.05 199.141 1124 199.141L1124.02 199.098Z"
    fill="var(--logo-ink)" />
  <path d="M55.4763 26.4391L58.8866 0H0V26.4391H55.4763Z" fill="var(--logo-ink)" />
  <path d="M39.8438 147.407L49.5455 72.2839H4.9909e-05V256.743H60.5602L80.048 147.407H39.8438Z"
    fill="#3688FF" />
  <path
    d="M192.42 59.361C182.782 40.2307 168.929 25.5705 150.903 15.3381C145.501 12.2662 139.761 9.6605 133.703 7.5208L115.401 103.702H159.757L76.2987 256.743H83.3735C109.449 256.743 131.69 251.574 150.14 241.236C168.569 230.897 182.634 216.131 192.356 196.959C202.058 177.765 206.909 154.8 206.909 128.043C206.909 101.286 202.079 78.5123 192.441 59.3821L192.42 59.361Z"
    fill="#3688FF" />
</svg>"""

CSS = """
:root{color-scheme:light;--logo-ink:#05213f;--surface:#fcfcfb;--plane:#f9f9f7;--ink:#0b0b0b;--ink2:#52514e;
--muted:#898781;--grid:#e1e0d9;--rule:#c3c2b7;--ring:rgba(11,11,11,.10);
--good:#0ca30c;--warn:#fab219;--serious:#ec835a;--crit:#d03b3b;}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;
--logo-ink:#ffffff;
--surface:#1a1a19;--plane:#0d0d0d;--ink:#fff;--ink2:#c3c2b7;--muted:#898781;
--grid:#2c2c2a;--rule:#383835;--ring:rgba(255,255,255,.10);}}
:root[data-theme="dark"]{color-scheme:dark;--logo-ink:#ffffff;--surface:#1a1a19;--plane:#0d0d0d;--ink:#fff;
--ink2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--rule:#383835;--ring:rgba(255,255,255,.10);}
*{box-sizing:border-box}
body{margin:0;background:var(--plane);color:var(--ink);
font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;
padding:0 16px env(safe-area-inset-bottom,0px);}
.wrap{max-width:1180px;margin:0 auto;padding-block:28px}
.masthead{background:var(--surface);border-bottom:1px solid var(--rule);
margin:0 -16px 20px;padding:0 16px;padding-top:env(safe-area-inset-top,0px)}
.mh{padding-block:14px;display:flex;gap:12px 24px;align-items:center;
justify-content:space-between;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:9px;margin:0;font-size:16px;font-weight:500;
letter-spacing:-.01em;color:var(--ink)}
.brand .mark{height:22px;width:auto;flex:none;display:block}
/* A hairline divider reads as "ThunderID, and this is its DX Dashboard" rather than
   running the product name into the wordmark. */
.brand span{padding-left:9px;border-left:1px solid var(--rule);line-height:1.1}
.seg{display:inline-flex;border:1px solid var(--rule);border-radius:7px;overflow:hidden}
.seg button{font:inherit;font-size:11px;line-height:1;padding:4px 8px;border:0;cursor:pointer;
background:transparent;color:var(--ink2);border-right:1px solid var(--rule)}
.seg button:last-child{border-right:0}
.seg button:hover{background:var(--plane);color:var(--ink)}
.seg button[aria-pressed="true"]{background:var(--plane);color:var(--ink);font-weight:600}
.how{margin:0 0 16px;font-size:13px}
.how summary{cursor:pointer;color:var(--ink2);width:fit-content;
list-style:none;display:inline-flex;align-items:center;gap:6px}
.how summary::-webkit-details-marker{display:none}
.how summary::before{content:"›";display:inline-block;color:var(--muted);
transition:transform .12s ease;font-size:15px;line-height:1}
.how[open] summary::before{transform:rotate(90deg)}
.how summary:hover{color:var(--ink)}
.how p{margin:8px 0 0;color:var(--ink2);max-width:78ch}
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
.dgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px}
.dcard{background:var(--surface);border:1px solid var(--ring);border-radius:9px;padding:12px}
.dcard h4{margin:0 0 8px;font-size:13px;display:flex;align-items:center;
justify-content:space-between;gap:8px}
.dcard .why{color:var(--ink2);font-size:12px;margin:0 0 9px}
ul.parts{list-style:none;margin:0 0 9px;padding:0;font-size:12px}
ul.parts li{display:flex;gap:7px;align-items:flex-start;padding:4px 0;
border-bottom:1px solid var(--grid)}
.pbody{flex:1;min-width:0}
.prow{display:flex;gap:8px;align-items:baseline;justify-content:space-between}
ul.parts li:last-child{border-bottom:0}
ul.parts .m{font-weight:700;width:11px;flex:none}
ul.parts .n{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px}
ul.parts .k{color:var(--muted);font-size:11px;white-space:nowrap;flex:none}
ul.parts .pkrow{display:block;margin:5px 0 1px}
.pkl{display:block;font-size:9.5px;text-transform:uppercase;letter-spacing:.05em;
color:var(--muted);margin-top:4px}
.pkg{display:flex;gap:3px;flex-wrap:wrap;margin-top:2px}
.pk{font-size:10px;line-height:1.5;padding:0 5px;border-radius:4px;
border:1px solid var(--grid);color:var(--muted);
font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.pk.on{color:#0ca30c;border-color:#0ca30c66;background:#0ca30c14;font-weight:600}
.ev{display:block;color:var(--muted);font-size:11px;
font-variant-numeric:tabular-nums;word-break:break-all}
.tsec{border-top:1px solid var(--grid);padding-top:8px;font-size:12px}
.tsec b{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--ink2)}
.tsec ul{list-style:none;margin:5px 0 0;padding:0}
.tsec li{color:var(--muted);font-size:11px;font-variant-numeric:tabular-nums;
word-break:break-all;padding:1px 0}
.tsec .none{color:var(--crit)}
.warn{background:var(--surface);border:1px solid #d03b3b60;border-left:3px solid #d03b3b;
border-radius:9px;padding:11px 14px;margin:0 0 14px;font-size:13px}
.warn b{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.06em;
color:var(--crit);margin-bottom:4px}
.warn ul{margin:0;padding-left:18px;color:var(--ink2)}
.summary{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:0 0 14px}
.chip{display:inline-flex;align-items:baseline;gap:5px;font-size:12px;color:var(--ink2);
background:var(--surface);border:1px solid var(--ring);border-radius:999px;padding:5px 11px}
.chip b{font-size:13px;font-variant-numeric:tabular-nums;color:inherit}
a.chip.is-link{text-decoration:none;cursor:pointer}
a.chip.is-link:hover{border-color:var(--rule);background:var(--plane)}
.chip.muted{color:var(--muted);border-style:dashed}
.stale{margin:-6px 0 14px;font-size:12px;color:var(--ink2)}
.stale code{font-size:11px}
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
// Theme: auto follows the operating system, light and dark override it in both
// directions. The stamp on <html> is what the stylesheet keys off.
(function(){
  var root=document.documentElement, KEY='parity-theme';
  function read(){
    try { var v=localStorage.getItem(KEY); return v==='light'||v==='dark'?v:'auto'; }
    catch(e){ return 'auto'; }
  }
  function apply(mode){
    if(mode==='auto') delete root.dataset.theme; else root.dataset.theme=mode;
    document.querySelectorAll('[data-set-theme]').forEach(function(b){
      b.setAttribute('aria-pressed', String(b.dataset.setTheme===mode));
    });
  }
  document.querySelectorAll('[data-set-theme]').forEach(function(b){
    b.addEventListener('click',function(){
      var mode=b.dataset.setTheme;
      try { mode==='auto'?localStorage.removeItem(KEY):localStorage.setItem(KEY,mode); }
      catch(e){}
      apply(mode);
    });
  });
  apply(read());
})();

const q=document.getElementById('q'),ax=document.getElementById('ax'),
show=document.getElementById('show');
function apply(){
  const term=q.value.trim().toLowerCase(), axis=ax.value, mode=show.value;
  document.querySelectorAll('section[data-axis]').forEach(sec=>{
    let shown=0;
    sec.querySelectorAll('tbody tr[data-name]').forEach(tr=>{
      const okAxis = axis==='all' || sec.dataset.axis===axis;
      const okTerm = !term || tr.dataset.name.includes(term);
      const okGap  = mode==='all'
                  || (mode==='gaps'     && tr.dataset.gap==='1')
                  || (mode==='orphan'   && tr.dataset.orphan==='1')
                  || (mode==='unknown'  && tr.dataset.unknown==='1');
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
[q,ax,show].forEach(el=>el.addEventListener('input',apply));

// The counts in the summary line are filters, not decoration: the interesting subsets are
// reachable without a wall of red above the data.
document.querySelectorAll('[data-show]').forEach(a=>{
  a.addEventListener('click',e=>{
    e.preventDefault();
    show.value=a.dataset.show; ax.value='all'; q.value='';
    apply();
    document.querySelector('.controls').scrollIntoView({block:'start',behavior:'smooth'});
  });
});

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


def _package_grid(index, present):
    """Which packages of a multi-package SDK carry a part, grouped by layer."""
    rows = []
    for layer, members in index.units_by_layer():
        chips = "".join(
            f'<span class="pk{" on" if u in present else ""}">{_esc(u)}</span>'
            for u in members
        )
        rows.append(f'<span class="pkl">{_esc(layer)}</span>'
                    f'<span class="pkg">{chips}</span>')
    return f'<span class="pkrow">{"".join(rows)}</span>'


def _parts_list(finding, index=None):
    if not finding.parts:
        return '<p class="why">Nothing to check against; see the reason above.</p>'
    head = ("Needs all of:" if finding.match_mode == "all" and len(finding.parts) > 1
            else "Needs any one of:" if finding.match_mode == "any" else "Needs:")
    items = []
    units = index.units() if index is not None else []
    for part in finding.parts:
        mark = "\u2713" if part.found else "\u2715"
        color = STATUS[SUPPORTED]["color"] if part.found else STATUS[MISSING]["color"]
        where = ({u for e in part.evidence
                  if (u := index.unit_of(e.rsplit(":", 1)[0]))} if units else set())
        if units:
            # Every package listed, present or not. A package is only expected to carry
            # what its layer implies, so absence is drawn as absence and not as a fault.
            ev = _package_grid(index, where)
        elif part.found:
            ev = "".join(f'<span class="ev">{_esc(e)}</span>' for e in part.evidence[:2])
        else:
            ev = '<span class="ev">not found</span>' 
        items.append(
            f'<li><span class="m" style="color:{color}" aria-hidden="true">{mark}</span>'
            f'<span class="pbody">'
            f'<span class="prow"><span class="n">{_esc(part.name)}</span>'
            f'<span class="k">{_esc(part.kind)}</span></span>{ev}</span></li>'
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


def _detail(cap, row, sdks, detail_id, cols, indexes=None):
    meta = [f'Discovered at <code>{_esc(cap.origin)}</code>.']
    if cap.notes:
        meta.append(_esc(cap.notes))
    if cap.inputs:
        meta.append("Declared inputs: " + ", ".join(
            f'<code>{_esc(i)}</code> ({_esc(t)})' for i, t in cap.inputs))
    cards = []
    for sdk in sdks:
        f = row.findings[sdk["id"]]
        m = STATUS[f.status]
        index = indexes.get(sdk["id"]) if indexes else None
        cards.append(
            f'<div class="dcard"><h4>{_esc(sdk["label"])}'
            f'<span class="pill" style="color:{m["color"]};background:{m["color"]}18;'
            f'border-color:{m["color"]}40"><i aria-hidden="true">{m["glyph"]}</i>'
            f'<span>{m["label"]}</span></span></h4>'
            + (f'<p class="why">{_esc(f.reason)}</p>' if f.reason else "")
            + _parts_list(f, index) + _tests_block(f) + '</div>'
        )
    return (f'<tr class="detail" id="{detail_id}" hidden><td colspan="{cols}">'
            f'<div class="dwrap"><p class="dmeta">{" ".join(meta)}</p>'
            f'<div class="dgrid">{"".join(cards)}</div></div></td></tr>')


def _matrix(axis, title, rows, sdks, indexes=None):
    if not rows:
        return ""
    def th(sdk):
        n = len(indexes[sdk["id"]].units()) if indexes and sdk["id"] in indexes else 0
        sub = (f'<span style="display:block;font-weight:400;text-transform:none;'
               f'letter-spacing:0;color:var(--muted)">{n} packages</span>' if n > 1 else "")
        return f"<th>{_esc(sdk['label'])}{sub}</th>"

    head = "".join(th(s) for s in sdks) + "<th>E2E</th>"
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
        scoredrow = getattr(r, "scored", True)
        orphan = scoredrow and r.is_total_gap
        unknown = scoredrow and all(f.status == UNDETERMINED for f in r.findings.values())
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
            f'data-name="{_esc(cap.name.lower())}" data-gap="{1 if r.is_gap else 0}" '
            f'data-orphan="{1 if orphan else 0}" data-unknown="{1 if unknown else 0}">'
            f'<td class="cap" title="{_esc(detail)}">'
            f'<span class="tw"><span class="caret" aria-hidden="true">&#9654;</span>'
            f'<b>{_esc(cap.name)}</b></span>'
            f'<span class="origin">{_esc(cap.origin)}</span></td>{cells}{e2e}</tr>'
        )
        body.append(_detail(cap, r, sdks, detail_id, len(sdks) + 2, indexes))
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


def _warnings(warnings):
    """Configuration problems, said out loud on the page.

    A suite that indexes nothing reads exactly like a suite that tests nothing, and the
    report cannot tell the reader which it is looking at unless it says so here.
    """
    if not warnings:
        return ""
    items = "".join(f"<li>{_esc(w)}</li>" for w in warnings)
    return (f'<div class="warn"><b>Check the configuration</b><ul>{items}</ul></div>')


def _summary(rows, stale, scored):
    """One line of counts, each one a filter on the tables below.

    The counts used to be a card of their own above the data, which pushed the tables off
    the screen and made the worst case the first thing read every time. The signal is the
    same; what changed is that reaching it is a click rather than a scroll past it.
    """
    orphan = [r for r in rows if getattr(r, "scored", True) and r.is_total_gap]
    unknown = [r for r in rows
               if getattr(r, "scored", True)
               and all(f.status == UNDETERMINED for f in r.findings.values())]
    gaps = [r for r in scored if r.is_gap]

    def chip(n, label, mode, tone=""):
        if not n:
            return (f'<span class="chip"><b>0</b> {label}</span>')
        style = f' style="color:{tone}"' if tone else ""
        return (f'<a class="chip is-link" href="#" data-show="{mode}"{style}>'
                f'<b>{n}</b> {label}</a>')

    bits = [
        chip(len(gaps), "short in at least one SDK", "gaps"),
        chip(len(orphan), "supported by no SDK", "orphan", STATUS[MISSING]["color"]),
        chip(len(unknown), "with no detector yet", "unknown", STATUS[UNDETERMINED]["color"]),
    ]
    stale_note = ""
    if stale:
        names = ", ".join(f"<code>{_esc(k)}</code>" for k in stale)
        stale_note = (f'<p class="stale">{len(stale)} stale override'
                      f'{"s" if len(stale) != 1 else ""} naming a capability that no longer '
                      f'exists upstream: {names}</p>')
    return (f'<div class="summary">{"".join(bits)}'
            f'<span class="chip muted">{len(scored)} scored</span></div>{stale_note}')


def render(result) -> str:
    rows, sdks = result["rows"], result["sdks"]
    scored = [r for r in rows if getattr(r, "scored", True)]

    tiles = "".join(_tile(s, scored) for s in sdks)
    axis_opts = "".join(f'<option value="{k}">{_esc(v)}</option>' for k, v in AXES.items())
    sections = "".join(
        _matrix(axis, title, [r for r in rows if r.capability.axis == axis], sdks,
                result.get("indexes"))
        for axis, title in AXES.items()
    )
    prov = " &middot; ".join(
        f"{_esc(s['label'])} <code>{_esc(s['commit'])}</code>" for s in sdks)
    total_gaps = sum(1 for r in scored if r.is_gap)

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>ThunderID DX Dashboard</title>
<!-- The mark, all-blue so it reads on a light or a dark browser tab. -->
<link rel="icon" href="data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%20207%20257%22%3E%3Cpath%20d%3D%22M55.4763%2026.4391L58.8866%200H0V26.4391H55.4763Z%22%20fill%3D%22%233688FF%22%2F%3E%3Cpath%20d%3D%22M39.8438%20147.407L49.5455%2072.2839H0V256.743H60.5602L80.048%20147.407H39.8438Z%22%20fill%3D%22%233688FF%22%2F%3E%3Cpath%20d%3D%22M192.42%2059.361C182.782%2040.2307%20168.929%2025.5705%20150.903%2015.3381C145.501%2012.2662%20139.761%209.6605%20133.703%207.5208L115.401%20103.702H159.757L76.2987%20256.743H83.3735C109.449%20256.743%20131.69%20251.574%20150.14%20241.236C168.569%20230.897%20182.634%20216.131%20192.356%20196.959C202.058%20177.765%20206.909%20154.8%20206.909%20128.043C206.909%20101.286%20202.079%2078.5123%20192.441%2059.3821L192.42%2059.361Z%22%20fill%3D%22%233688FF%22%2F%3E%3C%2Fsvg%3E">
<style>{CSS}</style>
<script>
// Runs before the body paints, so a stored choice does not flash the other theme first.
// Storage can be unavailable or throw (private window, blocked site data), and the page
// is correct without it: no stamp means the OS setting decides.
(function(){{
  try {{
    var t = localStorage.getItem('parity-theme');
    if (t === 'light' || t === 'dark') document.documentElement.dataset.theme = t;
  }} catch (e) {{}}
}})();
</script></head>
<body>
<header class="masthead"><div class="wrap mh">
  <h1 class="brand">{LOGO}<span>DX Dashboard</span></h1>
  <span class="seg" role="group" aria-label="Colour theme">
    <button type="button" data-set-theme="auto">Auto</button
    ><button type="button" data-set-theme="light">Light</button
    ><button type="button" data-set-theme="dark">Dark</button>
  </span>
</div></header>

<div class="wrap" style="padding-top:0">
<details class="how">
  <summary>How this is measured</summary>
  <p>Nothing here is hand-listed. Every run rediscovers the contract from source: the
  executors and wire constants from the server, the element palette from the console, and
  the client surface and configuration keys from the SDK specification. A capability is
  marked supported only where there is a file and a line in the SDK to justify it. Select
  any row for the evidence behind every cell.</p>
</details>

<div class="tiles" style="margin-bottom:18px">{tiles}</div>

{_warnings(result.get("warnings"))}
{_summary(rows, result["stale_overrides"], scored)}

<div class="controls">
  <input type="search" id="q" placeholder="Filter capabilities&hellip;" aria-label="Filter capabilities">
  <select id="ax" aria-label="Axis"><option value="all">All axes</option>{axis_opts}</select>
  <select id="show" aria-label="Show">
    <option value="all">All capabilities</option>
    <option value="gaps">Gaps only</option>
    <option value="orphan">Supported by no SDK</option>
    <option value="unknown">No detector yet</option>
  </select>
</div>

{sections}

<footer>
{len(scored)} capabilities scored, generated {_esc(result['generated'])}.<br>
Product <code>{_esc(result['product']['commit'])}</code> on
<code>{_esc(result['product']['branch'])}</code> &middot; measured against {prov}.<br>
Each row cites the file and line it was discovered from; select a row for the evidence
behind every cell.
</footer>
</div>
<script>{JS}</script>
</body></html>"""
