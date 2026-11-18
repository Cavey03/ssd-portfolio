"""Build the ITRI626 study-summary pages.

Run from anywhere:  python3 tools/summaries/build.py
Writes <unit folder>/summary.html for every study unit, plus summary-all.html at the portfolio root.
Every page is self-contained (inline CSS, JS and SVG; only Google Fonts load from the web, with fallbacks),
so each file works on its own when downloaded or opened from a clone.
The theme follows the "Periodic Table of Local LLMs" page: graph paper, element tiles, one colour per group.
"""
import html
from pathlib import Path

from content import UNITS

ROOT = Path(__file__).resolve().parents[2]
SRC_LABEL = {"book": "Trask", "mixed": "Trask+", "extra": "Extra"}

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@'
         '12..96,400;12..96,600;12..96,800&family=Atkinson+Hyperlegible:ital,wght@0,400;0,700;1,400&family='
         'JetBrains+Mono:wght@400;600&display=swap">')

THEME_INIT = ('<script>try{var t=localStorage.getItem("itri:theme");if(t==="light"||t==="dark")'
              'document.documentElement.dataset.theme=t}catch(e){}</script>')

CSS = r"""
:root {
  --bg: oklch(0.955 0.006 235); --paper: oklch(0.99 0.003 235); --ink: oklch(0.22 0.02 255);
  --muted: oklch(0.50 0.02 250); --line: oklch(0.86 0.012 240); --grid: oklch(0.90 0.012 240);
  --tint-l: 0.935; --ink-l: 0.47;
  --shadow: 0 1px 0 oklch(0.8 0.01 240), 0 6px 18px -10px oklch(0.3 0.03 250 / 0.35);
  --code-bg: oklch(0.97 0.005 240);
  --f-display: "Bricolage Grotesque", "Avenir Next Condensed", "Arial Narrow", system-ui, sans-serif;
  --f-body: "Atkinson Hyperlegible", "Segoe UI", system-ui, sans-serif;
  --f-mono: "JetBrains Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
  --hatch: repeating-linear-gradient(135deg, transparent 0 8px, color-mix(in oklch, var(--muted) 13%, transparent) 8px 9px);
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: oklch(0.165 0.014 255); --paper: oklch(0.21 0.017 255); --ink: oklch(0.94 0.008 240);
    --muted: oklch(0.70 0.02 240); --line: oklch(0.33 0.02 255); --grid: oklch(0.205 0.016 255);
    --tint-l: 0.285; --ink-l: 0.82; --code-bg: oklch(0.185 0.015 255);
    --shadow: 0 1px 0 oklch(0.12 0.01 255), 0 8px 20px -12px oklch(0 0 0 / 0.7);
    color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --bg: oklch(0.165 0.014 255); --paper: oklch(0.21 0.017 255); --ink: oklch(0.94 0.008 240);
  --muted: oklch(0.70 0.02 240); --line: oklch(0.33 0.02 255); --grid: oklch(0.205 0.016 255);
  --tint-l: 0.285; --ink-l: 0.82; --code-bg: oklch(0.185 0.015 255);
  --shadow: 0 1px 0 oklch(0.12 0.01 255), 0 8px 20px -12px oklch(0 0 0 / 0.7);
  color-scheme: dark;
}
* { box-sizing: border-box; }
[hidden] { display: none !important; }
html { -webkit-text-size-adjust: 100%; scroll-padding-top: 72px; }
body {
  margin: 0; background-color: var(--bg); color: var(--ink); font-family: var(--f-body);
  font-size: 15.5px; line-height: 1.55;
  background-image: linear-gradient(var(--grid) 1px, transparent 1px), linear-gradient(90deg, var(--grid) 1px, transparent 1px);
  background-size: 28px 28px;
}
a { color: inherit; }
button { font: inherit; color: inherit; }
:focus-visible { outline: 2px solid var(--ink); outline-offset: 2px; }
.wrap { max-width: 1180px; margin: 0 auto; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
.g { --tint: oklch(var(--tint-l) calc(var(--c) * 0.42) var(--h)); --stroke: oklch(var(--ink-l) var(--c) var(--h)); }

/* top bar */
.topbar { position: sticky; top: 0; z-index: 6; background: color-mix(in oklch, var(--bg) 88%, transparent);
  backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); border-bottom: 1px solid var(--line); }
.topbar .wrap { display: flex; flex-wrap: wrap; gap: 8px 14px; align-items: center; padding-block: 9px; }
.brand { font-family: var(--f-display); font-weight: 800; font-size: 16px; letter-spacing: -0.02em; text-decoration: none; margin-right: auto; }
.brand span { color: var(--muted); font-weight: 400; }
.units { display: flex; flex-wrap: wrap; gap: 6px; }
.ulink { font-family: var(--f-mono); font-size: 12px; font-weight: 600; text-decoration: none; padding: 4px 8px;
  border: 1.5px solid var(--line); border-radius: 4px; background: var(--paper); color: var(--stroke); }
.ulink:hover { border-color: var(--stroke); }
.ulink[aria-current="page"] { background: var(--tint); border-color: var(--stroke); }
.ulink.all { color: var(--ink); }
.tools { display: flex; gap: 6px; }
.btn { border: 1.5px solid var(--line); background: var(--paper); border-radius: 4px; padding: 4px 10px; cursor: pointer; font-size: 13px; }
.btn:hover { border-color: var(--ink); }
.btn[aria-pressed="true"] { background: var(--ink); color: var(--paper); border-color: var(--ink); }

/* hero */
.hero { padding-block: 40px 26px; display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 28px 48px; align-items: end; }
.eyebrow { font-family: var(--f-mono); font-size: 12px; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin: 0 0 14px; }
h1 { font-family: var(--f-display); font-weight: 800; font-size: clamp(36px, 6vw, 76px); line-height: .94;
  letter-spacing: -0.035em; margin: 0; text-wrap: balance; font-variation-settings: "opsz" 96; }
h1 .thin { font-weight: 400; display: block; font-size: .46em; letter-spacing: -0.01em; margin-bottom: .2em; color: var(--muted); }
h1 .accent { color: var(--stroke); }
.lede { max-width: 62ch; margin: 18px 0 0; font-size: 16px; color: var(--muted); }
.lede b { color: var(--ink); }
.stats { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 18px; }
.stat { font-family: var(--f-mono); font-size: 12px; border: 1.5px solid var(--line); background: var(--paper); padding: 3px 9px; border-radius: 4px; color: var(--muted); }
.stat b { color: var(--ink); }
.key { display: flex; gap: 18px; align-items: center; margin: 0; }
.key .el { width: 200px; }
.key dl { margin: 0; display: grid; gap: 10px; font-size: 13px; max-width: 230px; }
.key dt { font-family: var(--f-mono); font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); }
.key dd { margin: 2px 0 0; }
.key-cap { font-family: var(--f-mono); font-size: 11px; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin-bottom: 8px; }
.hatch-sw { display: inline-block; width: 26px; height: 12px; border: 1.5px dashed var(--muted); border-radius: 2px; background-image: var(--hatch); vertical-align: -2px; margin-right: 4px; }

/* legend chips */
.legend { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 232px), 1fr)); gap: 8px; padding-block: 6px 22px; }
.chip { display: grid; grid-template-columns: 40px minmax(0, 1fr); gap: 10px; align-items: center; text-align: left;
  padding: 7px 10px 7px 7px; border: 1.5px solid var(--line); border-radius: 4px; background: var(--paper);
  cursor: pointer; text-decoration: none; transition: border-color .15s, transform .15s; }
.chip:hover { border-color: var(--stroke, var(--ink)); transform: translateY(-1px); }
.chip[aria-pressed="true"] { border-color: var(--stroke, var(--ink)); background: var(--tint, var(--paper)); box-shadow: inset 0 0 0 1px var(--stroke, var(--ink)); }
.chip .sw { height: 40px; border-radius: 3px; display: grid; place-items: center; background: var(--tint, var(--bg));
  border: 1.5px solid var(--stroke, var(--ink)); font-family: var(--f-display); font-weight: 800; font-size: 14px;
  color: var(--stroke, var(--ink)); letter-spacing: -0.02em; }
.chip.xt .sw { background-image: var(--hatch); border-style: dashed; }
.chip .nm { font-weight: 700; font-size: 13.5px; line-height: 1.2; display: block; }
.chip .ct { font-family: var(--f-mono); font-size: 11px; color: var(--muted); display: block; margin-top: 3px; }

/* search toolbar (combined page) */
.toolbar { position: sticky; top: 49px; z-index: 5; background: color-mix(in oklch, var(--bg) 88%, transparent);
  backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); border-bottom: 1px solid var(--line); }
.toolbar .wrap { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; padding-block: 9px; }
.search { flex: 1 1 260px; position: relative; min-width: 0; }
.search input { width: 100%; padding: 8px 12px 8px 34px; border: 1.5px solid var(--line); border-radius: 4px; background: var(--paper); font: inherit; color: inherit; }
.search input:focus { border-color: var(--ink); outline: none; }
.search svg { position: absolute; left: 11px; top: 50%; transform: translateY(-50%); color: var(--muted); }
.count { font-family: var(--f-mono); font-size: 12px; color: var(--muted); margin-left: auto; }

/* outcome sections */
main { padding-block: 22px 40px; }
.section { margin-bottom: 46px; }
.section-head { display: flex; align-items: baseline; gap: 4px 14px; flex-wrap: wrap; padding-bottom: 10px; margin-bottom: 14px; border-bottom: 2px solid var(--stroke); }
.section-head .code { font-family: var(--f-mono); font-size: 12px; font-weight: 600; letter-spacing: .1em; color: var(--stroke); text-transform: uppercase; }
.section-head h2 { font-family: var(--f-display); font-weight: 800; font-size: clamp(21px, 2.6vw, 29px); letter-spacing: -0.02em; margin: 0; line-height: 1.12; flex: 1 1 420px; text-wrap: balance; }
.o-grid { display: grid; grid-template-columns: minmax(0, 252px) minmax(0, 1fr); gap: 14px; align-items: start; position: relative; }
.o-side { position: sticky; top: 66px; }
.el { position: relative; background: var(--paper); border: 1.5px solid var(--stroke); border-radius: 3px; display: flex;
  flex-direction: column; min-width: 0; box-shadow: var(--shadow); }
.el .cell { background: var(--tint); padding: 8px 10px 10px; border-bottom: 1.5px solid var(--stroke); display: grid; grid-template-columns: auto 1fr auto; align-items: start; gap: 2px 10px; }
.el.xt .cell { background-image: var(--hatch); }
.el .num { font-family: var(--f-mono); font-size: 11px; font-weight: 600; color: var(--stroke); }
.el .gc { font-family: var(--f-mono); font-size: 10px; letter-spacing: .1em; text-transform: uppercase; color: var(--stroke); grid-column: 3; text-align: right; }
.el .sym { grid-column: 1 / -1; font-family: var(--f-display); font-weight: 800; font-size: 44px; line-height: .95; letter-spacing: -0.04em; color: var(--stroke); font-variation-settings: "opsz" 96; }
.el .name { font-family: var(--f-display); font-weight: 600; font-size: 16px; line-height: 1.2; margin: 0; letter-spacing: -0.01em; grid-column: 1 / -1; text-wrap: balance; }
.el .body { padding: 10px 12px 12px; display: grid; gap: 10px; }
.el .def { margin: 0; font-size: 14px; line-height: 1.5; }
.cites { display: flex; flex-wrap: wrap; gap: 4px; }
.cite { display: inline-block; font-family: var(--f-mono); font-size: 11px; font-weight: 600; color: var(--stroke);
  border: 1px solid color-mix(in oklch, var(--stroke) 50%, transparent); background: var(--tint); padding: 0 6px;
  border-radius: 3px; white-space: nowrap; vertical-align: 1px; line-height: 1.6; }
.card { background: var(--paper); border: 1.5px solid var(--line); border-radius: 4px; padding: 18px 20px 8px; box-shadow: var(--shadow); min-width: 0; }
.card > :first-child { margin-top: 0; }
.card p { margin: 0 0 12px; max-width: 76ch; }
.card h3 { font-family: var(--f-display); font-weight: 700; font-size: 17.5px; letter-spacing: -0.01em; margin: 22px 0 8px; color: var(--stroke); }
.card ul, .card ol { margin: 0 0 12px; padding-left: 22px; max-width: 76ch; }
.card li { margin-bottom: 5px; }
.eq { font-family: var(--f-mono); font-size: 13.5px; background: var(--tint); border-left: 3px solid var(--stroke); padding: 10px 14px; border-radius: 0 3px 3px 0; margin: 4px 0 14px; overflow-x: auto; line-height: 1.75; white-space: nowrap; }
pre { font-family: var(--f-mono); font-size: 12.5px; line-height: 1.55; background: var(--code-bg); border: 1px solid var(--line); border-radius: 3px; padding: 12px 14px; overflow-x: auto; margin: 4px 0 14px; }
pre .c { color: var(--muted); font-style: italic; }
code { font-family: var(--f-mono); font-size: .88em; }
p code, li code, td code { background: var(--code-bg); border: 1px solid var(--line); border-radius: 3px; padding: 0 4px; }
.code-note { font-family: var(--f-mono); font-size: 11px; color: var(--muted); margin: -8px 0 14px; }
.xtra { position: relative; border: 1.5px dashed var(--muted); border-radius: 4px; padding: 32px 16px 4px; margin: 8px 0 16px; background-image: var(--hatch); }
.xtra .xtra { border: 0; padding: 0; background: none; }
.xtag { position: absolute; top: -1px; left: -1px; font-family: var(--f-mono); font-size: 10.5px; letter-spacing: .08em; text-transform: uppercase; background: var(--ink); color: var(--paper); padding: 3px 9px; border-radius: 4px 0 4px 0; }
.xtra > h3:first-of-type { margin-top: 2px; }
.xtra pre, .xtra .tbl, .xtra .fig, .xtra .eq { background-color: var(--paper); }
.xtra .eq { background: var(--paper); }
.tbl-wrap { overflow-x: auto; margin: 4px 0 14px; border: 1px solid var(--line); border-radius: 3px; }
.tbl { border-collapse: collapse; width: 100%; font-size: 13.5px; background: var(--paper); }
.tbl th { font-family: var(--f-mono); font-size: 10.5px; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); text-align: left; font-weight: 600; border-bottom: 1.5px solid var(--stroke); padding: 7px 9px; }
.tbl td { border-bottom: 1px solid var(--line); padding: 7px 9px; vertical-align: top; }
.tbl tr:last-child td { border-bottom: 0; }
.tbl tr.xrow td { background-image: var(--hatch); }
.tbl tr.xrow td:first-child::after { content: "not in Trask"; display: block; font-family: var(--f-mono); font-size: 9.5px; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }
.fig { margin: 6px 0 16px; padding: 12px; border: 1px solid var(--line); border-radius: 4px; background: var(--paper); }
.fig svg { display: block; width: 100%; height: auto; max-width: 520px; margin: 0 auto; }
.fig figcaption { font-family: var(--f-mono); font-size: 11px; color: var(--muted); margin-top: 8px; text-align: center; }
.plots { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
.plots.two { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.plots svg { max-width: none; }
svg text { font-family: var(--f-mono); font-size: 10px; }
svg .lbl { fill: var(--ink); } svg .cap { fill: var(--muted); } svg .strong { font-weight: 700; }
svg .nd { fill: var(--tint); stroke: var(--stroke); stroke-width: 1.5; }
svg .nd.soft { fill: none; stroke: var(--line); }
svg .nd.strongfill { fill: color-mix(in oklch, var(--stroke) 24%, var(--paper)); }
svg .ed { stroke: var(--stroke); stroke-opacity: .35; stroke-width: 1.2; }
svg .ed.strong { stroke-opacity: .75; }
svg .ax { stroke: var(--line); stroke-width: 1; }
svg .dash { stroke-dasharray: 4 3; }
svg .cv { fill: none; stroke: var(--stroke); stroke-width: 2.2; stroke-linejoin: round; }
svg .cv.soft { stroke-opacity: .55; }
svg .arw { fill: none; stroke: var(--ink); stroke-width: 1.4; }
svg .arw.thin { stroke-width: 1.1; stroke-opacity: .7; }
svg .ahd { fill: var(--ink); }
svg .pt { fill: var(--stroke); }
svg .ptw { fill: var(--paper); stroke: var(--stroke); stroke-width: 1.5; }
svg .ring { fill: none; stroke: var(--ink); stroke-width: 1.3; }
svg .cen { stroke: var(--ink); stroke-width: 2.6; stroke-linecap: round; }
svg .cell { fill: var(--paper); stroke: var(--line); stroke-width: 1; }
svg .cell.on, svg .heat { fill: var(--stroke); }
svg .win { fill: none; stroke: var(--ink); stroke-width: 2; }
svg .b0 { fill: color-mix(in oklch, var(--stroke) 8%, var(--paper)); }
svg .b1 { fill: color-mix(in oklch, var(--stroke) 18%, var(--paper)); }
svg .b2 { fill: color-mix(in oklch, var(--stroke) 28%, var(--paper)); }
svg .b3 { fill: color-mix(in oklch, var(--stroke) 38%, var(--paper)); }
.flow { display: flex; flex-wrap: wrap; align-items: stretch; gap: 6px; margin: 6px 0 8px; }
.step { flex: 1 1 120px; min-width: 0; border: 1.5px solid var(--stroke); background: var(--tint); border-radius: 3px; padding: 8px 10px; display: grid; gap: 2px; align-content: start; }
.step b { font-family: var(--f-display); font-size: 15px; line-height: 1.2; }
.step span { font-size: 12.5px; color: var(--muted); line-height: 1.35; }
.step.xstep { background-image: var(--hatch); border-style: dashed; }
.step.xstep span::after { content: " · not in Trask"; font-family: var(--f-mono); font-size: 10px; text-transform: uppercase; letter-spacing: .06em; }
.flow .arrow { align-self: center; color: var(--muted); font-family: var(--f-mono); }
.loop { font-family: var(--f-mono); font-size: 11.5px; color: var(--muted); margin: 0 0 14px; }
.split { display: flex; flex-wrap: wrap; gap: 4px; margin: 4px 0 4px; }
.split div { border: 1.5px solid var(--stroke); border-radius: 3px; padding: 8px 10px; min-width: 76px; display: grid; background: var(--tint); }
.split div + div { background: var(--paper); }
.split div:last-child { background-image: var(--hatch); }
.split b { font-family: var(--f-display); }
.split span { font-size: 12px; color: var(--muted); }
.split-cap { font-family: var(--f-mono); font-size: 11px; color: var(--muted); margin: 0 0 14px; }
.tl { margin: 4px 0 14px; }
.tl-row { display: flex; flex-wrap: wrap; gap: 4px; align-items: center; margin-bottom: 6px; }
.tl-k { font-family: var(--f-mono); font-size: 11px; color: var(--muted); width: 92px; }
.blk { flex: 1 1 70px; border: 1.5px solid var(--stroke); border-radius: 3px; padding: 6px 8px; font-size: 12.5px; text-align: center; background: var(--paper); }
.blk.frozen { background-image: var(--hatch); border-style: dashed; }
.blk.head { background-color: var(--tint); }
.blk.new { background: var(--stroke); color: var(--paper); font-weight: 700; }
.tl-cap { font-size: 12px; color: var(--muted); margin: 4px 0 0 !important; }
.mine { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 4px 12px; align-items: center; text-decoration: none;
  border: 1.5px solid var(--stroke); background: var(--tint); border-radius: 4px; padding: 10px 12px; margin: 10px 0 12px; transition: transform .15s; }
.mine:hover { transform: translateY(-1px); }
.mine-k { font-family: var(--f-mono); font-size: 10.5px; letter-spacing: .08em; text-transform: uppercase; color: var(--stroke); font-weight: 600; }
.mine-t { font-weight: 700; font-size: 14px; }
.mine-a { color: var(--stroke); font-family: var(--f-mono); }
.terms { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 210px), 1fr)); gap: 8px; margin-top: 12px; }
.term { background: var(--paper); border: 1.5px solid var(--line); border-left: 4px solid var(--stroke); border-radius: 3px; padding: 8px 10px; }
.term.xt { border-left-style: dashed; background-image: var(--hatch); }
.term b { display: block; font-family: var(--f-display); font-size: 14.5px; line-height: 1.25; }
.term .d { display: block; font-size: 13px; color: var(--muted); margin-top: 2px; }
.term .xk { font-family: var(--f-mono); font-size: 9.5px; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }

/* test-myself mode */
.recall .o-grid:not(.revealed) { cursor: pointer; }
.recall .o-grid:not(.revealed) .card, .recall .o-grid:not(.revealed) .el .def {
  filter: blur(7px); opacity: .45; user-select: none; pointer-events: none; }
.recall .o-grid:not(.revealed)::after { content: "Explain it first, then tap to reveal"; position: absolute; left: 50%; top: 90px; transform: translateX(-50%);
  font-family: var(--f-mono); font-size: 11px; letter-spacing: .08em; text-transform: uppercase; background: var(--paper);
  border: 1px solid var(--line); padding: 4px 9px; border-radius: 3px; color: var(--muted); white-space: nowrap; z-index: 2; }
.recall .term:not(.revealed) { cursor: pointer; }
.recall .term:not(.revealed) .d { filter: blur(5px); opacity: .5; user-select: none; }

/* combined page: unit banners */
.unit-block + .unit-block { margin-top: 18px; }
.ubanner { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 6px 18px; align-items: center; padding: 16px 18px;
  border: 1.5px solid var(--stroke); background: var(--tint); border-radius: 4px; margin-bottom: 24px; box-shadow: var(--shadow); }
.ubanner .usym { font-family: var(--f-display); font-weight: 800; font-size: 46px; color: var(--stroke); letter-spacing: -0.04em; line-height: 1; }
.ubanner h2 { font-family: var(--f-display); font-weight: 800; font-size: clamp(22px, 3vw, 32px); letter-spacing: -0.02em; margin: 0; line-height: 1.05; }
.ubanner p { margin: 4px 0 0; color: var(--muted); font-size: 13.5px; }
.ubanner a { font-family: var(--f-mono); font-size: 12px; color: var(--stroke); font-weight: 600; white-space: nowrap; }
.empty { text-align: center; padding: 50px 0; color: var(--muted); }

.foot { border-top: 1px solid var(--line); padding-block: 20px 44px; color: var(--muted); font-size: 13px; }
.foot p { margin: 0 0 6px; max-width: 90ch; }

@media (max-width: 860px) {
  .o-grid { grid-template-columns: minmax(0, 1fr); }
  .o-side { position: static; }
  .hero { grid-template-columns: minmax(0, 1fr); padding-block: 28px 16px; }
  .toolbar { position: static; }
}
@media (max-width: 560px) {
  .key { flex-direction: column; align-items: flex-start; }
  .plots, .plots.two { grid-template-columns: minmax(0, 1fr); }
  .flow { flex-direction: column; }
  .flow .arrow { transform: rotate(90deg); align-self: center; }
  .mine { grid-template-columns: minmax(0, 1fr) auto; }
  .mine-k { grid-column: 1 / -1; }
  .ubanner { grid-template-columns: minmax(0, 1fr); }
  .card { padding: 14px 14px 6px; }
  .count { margin-left: 0; width: 100%; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }
@media print {
  .topbar, .toolbar, .tools, .legend { display: none !important; }
  body { background: #fff; }
  .card, .el, .ubanner { box-shadow: none; }
  .o-side { position: static; }
  .section { break-inside: avoid-page; }
}
"""

JS = r"""
(function () {
  var root = document.documentElement;
  var tbtn = document.getElementById("themeBtn");
  function stored() { try { return localStorage.getItem("itri:theme"); } catch (e) { return null; } }
  function store(v) { try { if (v) localStorage.setItem("itri:theme", v); else localStorage.removeItem("itri:theme"); } catch (e) {} }
  var cur = stored(); if (cur !== "light" && cur !== "dark") cur = null;
  function apply() {
    if (cur) root.dataset.theme = cur; else delete root.dataset.theme;
    tbtn.textContent = "Theme: " + (cur ? cur : "auto");
  }
  apply();
  tbtn.addEventListener("click", function () { cur = cur === null ? "light" : cur === "light" ? "dark" : null; store(cur); apply(); });

  var rbtn = document.getElementById("recallBtn");
  rbtn.addEventListener("click", function () {
    var on = document.body.classList.toggle("recall");
    rbtn.setAttribute("aria-pressed", on ? "true" : "false");
    document.querySelectorAll(".revealed").forEach(function (e) { e.classList.remove("revealed"); });
  });
  document.addEventListener("click", function (e) {
    if (!document.body.classList.contains("recall")) return;
    var t = e.target.closest(".o-grid, .term");
    if (t && !t.classList.contains("revealed")) { t.classList.add("revealed"); e.preventDefault(); }
  });

  var q = document.getElementById("q");
  var chips = Array.prototype.slice.call(document.querySelectorAll("[data-filter]"));
  if (!q && !chips.length) return;
  var unit = "";
  function run() {
    var s = q ? q.value.trim().toLowerCase() : "";
    var n = 0;
    document.querySelectorAll(".outcome").forEach(function (o) {
      var ok = (!unit || o.dataset.unit === unit) && (!s || o.textContent.toLowerCase().indexOf(s) !== -1);
      o.hidden = !ok; if (ok) n++;
    });
    document.querySelectorAll(".unit-block").forEach(function (b) { b.hidden = !b.querySelector(".outcome:not([hidden])"); });
    document.getElementById("count").textContent = n + (n === 1 ? " outcome" : " outcomes");
    document.getElementById("empty").hidden = n !== 0;
  }
  chips.forEach(function (ch) {
    ch.addEventListener("click", function () {
      unit = ch.dataset.filter;
      chips.forEach(function (x) { x.setAttribute("aria-pressed", x === ch ? "true" : "false"); });
      run();
    });
  });
  if (q) {
    q.addEventListener("input", run);
    document.addEventListener("keydown", function (e) {
      if (e.key === "/" && document.activeElement !== q) { e.preventDefault(); q.focus(); }
    });
  }
  run();
})();
"""


def gvars(u):
    return f'--h:{u["h"]};--c:{u["c"]}'


def tile(o, u):
    xt = " xt" if o["src"] == "extra" else ""
    cites = "".join(f'<span class="cite">{html.escape(c)}</span>' for c in o["cites"])
    return (f'<article class="el g{xt}" style="{gvars(u)}">'
            f'<div class="cell"><span class="num">{o["num"]}</span><span class="gc">{SRC_LABEL[o["src"]]}</span>'
            f'<div class="sym" aria-hidden="true">{o["sym"]}</div><h3 class="name">{o["short"]}</h3></div>'
            f'<div class="body"><p class="def">{o["tldr"]}</p><div class="cites">{cites}</div></div></article>')


def terms(o):
    out = []
    for t in o["terms"]:
        xt = " xt" if t["extra"] else ""
        xk = '<span class="xk">not in Trask</span>' if t["extra"] else ""
        out.append(f'<div class="term{xt}">{xk}<b>{t["term"]}</b><span class="d">{t["def"]}</span></div>')
    return '<div class="terms">' + "".join(out) + "</div>"


def section(o, u, sid):
    return (f'<section class="section g outcome" id="{sid}" data-unit="{u["id"]}" style="{gvars(u)}">'
            f'<div class="section-head"><span class="code">{u["code"]} · {o["num"]}</span><h2>{o["title"]}</h2></div>'
            f'<div class="o-grid"><div class="o-side">{tile(o, u)}</div>'
            f'<div class="card">{"".join(o["body"])}</div></div>{terms(o)}</section>')


def counts(outcomes):
    c = {"book": 0, "mixed": 0, "extra": 0}
    for o in outcomes:
        c[o["src"]] += 1
    return c


def topbar(current, prefix):
    links = []
    for u in UNITS:
        cur = ' aria-current="page"' if u["id"] == current else ""
        # On the combined page, jump within the page so it works even when opened as a single file
        href = f'#{u["id"]}' if current == "all" else f'{prefix}{u["folder"]}/summary.html'
        links.append(f'<a class="ulink g" style="{gvars(u)}" href="{href}"{cur}>{u["code"]}</a>')
    cur = ' aria-current="page"' if current == "all" else ""
    links.append(f'<a class="ulink all" href="{prefix}summary-all.html"{cur}>All</a>')
    return (f'<nav class="topbar" aria-label="Study units"><div class="wrap">'
            f'<a class="brand" href="{prefix}summary-all.html">ITRI626 <span>· study summaries</span></a>'
            f'<div class="units">{"".join(links)}</div>'
            f'<div class="tools"><button class="btn" id="recallBtn" aria-pressed="false" '
            f'title="Blur the explanations so you can test yourself">Test myself</button>'
            f'<button class="btn" id="themeBtn">Theme: auto</button></div></div></nav>')


def keyfig(u):
    sample = {"num": "3.3", "src": "mixed", "sym": "Gd", "short": "Outcome name", "cites": ["Ch 4 · p 56"],
              "tldr": "The outcome in one or two sentences."}
    return (f'<figure class="key g" style="{gvars(u)}" aria-label="How to read this page">'
            f'<div><div class="key-cap">Reading a tile</div>{tile(sample, u)}</div>'
            '<dl>'
            '<div><dt>Ch 4 · p 56</dt><dd>Chapter and printed page in Trask, <i>Grokking Deep Learning</i>, '
            'so you can check it against the book</dd></div>'
            '<div><dt>Corner tag</dt><dd><b>Trask</b> all from the book · <b>Trask+</b> book plus extras · '
            '<b>Extra</b> not in the book</dd></div>'
            '<div><dt><span class="hatch-sw"></span>Hatched</dt><dd>Added from other sources: <b>not in Trask</b></dd></div>'
            '</dl></figure>')


def footer():
    return ('<footer class="wrap foot">'
            '<p><b>Source:</b> Andrew W. Trask, <i>Grokking Deep Learning</i> (Manning, 2019). Citations give the '
            'chapter and printed page. Explanations are my own summaries, not quotes; code marked as from the book is '
            'adapted from the book\'s notebooks.</p>'
            '<p><b>Not in Trask</b> sections (hatched) come from general machine-learning practice, the Scikit-Learn, '
            'PyTorch and Unsloth documentation, and my own portfolio work.</p>'
            '<p>Generated by <code>tools/summaries/build.py</code> · ITRI626 portfolio.</p></footer>')


def page(title, desc, body, current, prefix, hue_unit):
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
            f'<title>{title}</title><meta name="description" content="{html.escape(desc)}">'
            f'{FONTS}{THEME_INIT}<style>{CSS}</style></head>'
            f'<body>{topbar(current, prefix)}{body}{footer()}<script>{JS}</script></body></html>')


def unit_page(u):
    prefix = "../"
    c = counts(u["outcomes"])
    chips = "".join(
        f'<a class="chip g{" xt" if o["src"] == "extra" else ""}" style="{gvars(u)}" href="#{o["id"]}">'
        f'<span class="sw">{o["sym"]}</span><span><span class="nm">{o["short"]}</span>'
        f'<span class="ct">{u["code"]} · {o["num"]} · {SRC_LABEL[o["src"]]}</span></span></a>'
        for o in u["outcomes"])
    hero = (f'<header class="wrap hero g" style="{gvars(u)}"><div>'
            f'<p class="eyebrow">ITRI626 · {u["kicker"]} · study summary</p>'
            f'<h1><span class="thin">{u["code"]}</span><span class="accent">{u["title"]}</span></h1>'
            f'<p class="lede">{u["lede"]}</p>'
            f'<div class="stats"><span class="stat"><b>{len(u["outcomes"])}</b> outcomes</span>'
            f'<span class="stat"><b>{c["book"]}</b> from Trask</span><span class="stat"><b>{c["mixed"]}</b> Trask + extras</span>'
            f'<span class="stat"><b>{c["extra"]}</b> not in Trask</span>'
            f'<span class="stat">{u["chapters"]}</span></div></div>{keyfig(u)}</header>')
    legend = f'<nav class="wrap legend" aria-label="Outcomes on this page">{chips}</nav>'
    sections = "".join(section(o, u, o["id"]) for o in u["outcomes"])
    body = hero + legend + f'<main class="wrap">{sections}</main>'
    html_out = page(f'{u["code"]} · {u["title"]}', f'ITRI626 {u["code"]} study summary: {u["title"]}', body,
                    u["id"], prefix, u)
    return html_out.replace("{root}", prefix)


def all_page():
    prefix = ""
    every = [o for u in UNITS for o in u["outcomes"]]
    c = counts(every)
    chips = ['<button class="chip" data-filter="" aria-pressed="true"><span class="sw">All</span>'
             f'<span><span class="nm">Every unit</span><span class="ct">{len(every)} outcomes</span></span></button>']
    for u in UNITS:
        chips.append(f'<button class="chip g" style="{gvars(u)}" data-filter="{u["id"]}" aria-pressed="false">'
                     f'<span class="sw">{u["code"].replace("–", "")[:5]}</span><span><span class="nm">{u["title"]}</span>'
                     f'<span class="ct">{len(u["outcomes"])} outcomes</span></span></button>')
    first = UNITS[0]
    hero = (f'<header class="wrap hero g" style="{gvars(first)}"><div>'
            '<p class="eyebrow">ITRI626 · every study unit · study summary</p>'
            '<h1><span class="thin">ITRI626, every outcome</span>Machine learning to LLM agents</h1>'
            '<p class="lede">All the learning outcomes of the module on one page, summarised from Trask\'s '
            '<b>Grokking Deep Learning</b> with chapter and page references, plus clearly marked extras for what the '
            'book doesn\'t cover. Filter by unit, search, or switch on <b>Test myself</b> to hide the answers.</p>'
            f'<div class="stats"><span class="stat"><b>{len(UNITS)}</b> units</span>'
            f'<span class="stat"><b>{len(every)}</b> outcomes</span><span class="stat"><b>{c["book"]}</b> from Trask</span>'
            f'<span class="stat"><b>{c["mixed"]}</b> Trask + extras</span><span class="stat"><b>{c["extra"]}</b> not in Trask</span>'
            f'</div></div>{keyfig(first)}</header>')
    legend = f'<nav class="wrap legend" aria-label="Filter by study unit">{"".join(chips)}</nav>'
    toolbar = ('<div class="toolbar"><div class="wrap"><label class="search">'
               '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="7" cy="7" r="5" '
               'stroke="currentColor" stroke-width="1.6"/><path d="M11 11l3.5 3.5" stroke="currentColor" stroke-width="1.6" '
               'stroke-linecap="round"/></svg><input id="q" type="search" placeholder="Search every outcome…  ( / )" '
               'autocomplete="off" aria-label="Search the outcomes"></label><span class="count" id="count"></span>'
               '</div></div>')
    blocks = []
    for u in UNITS:
        banner = (f'<div class="ubanner g" style="{gvars(u)}"><div class="usym">{u["code"]}</div>'
                  f'<div><h2>{u["title"]}</h2><p>{u["lede"]}</p></div>'
                  f'<a href="{u["folder"]}/summary.html">Unit page →</a></div>')
        secs = "".join(section(o, u, f'{u["id"]}-{o["id"]}') for o in u["outcomes"])
        blocks.append(f'<div class="unit-block" id="{u["id"]}">{banner}{secs}</div>')
    empty = '<p class="empty" id="empty" hidden>No outcome matches that search.</p>'
    body = hero + legend + toolbar + f'<main class="wrap">{"".join(blocks)}{empty}</main>'
    return page("ITRI626 Study Summaries", "Every ITRI626 learning outcome, summarised from Trask with extras marked",
                body, "all", prefix, first).replace("{root}", prefix)


def main():
    for u in UNITS:
        out = ROOT / u["folder"] / "summary.html"
        out.parent.mkdir(exist_ok=True)
        out.write_text(unit_page(u), encoding="utf-8")
        print(f"{out.relative_to(ROOT)}  {out.stat().st_size // 1024} KB")
    out = ROOT / "summary-all.html"
    out.write_text(all_page(), encoding="utf-8")
    print(f"{out.relative_to(ROOT)}  {out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
