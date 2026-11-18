"""Turn learning-process.md into a styled HTML page (for the PDF and Word versions)."""
import re
import sys
from pathlib import Path
from markdown_it import MarkdownIt

HERE = Path(__file__).resolve().parent.parent  # su5-7-llm-agents/
REPO = "https://github.com/Cavey03/ssd-portfolio/blob/main/su5-7-llm-agents/"
src = (HERE / sys.argv[1]).read_text()
# Relative links point into the repo: make them GitHub links so they work from a PDF or Word file.
src = re.sub(r"\]\((?!https?://|#)([^)]+)\)", lambda m: f"]({REPO}{m.group(1)})", src)
body = MarkdownIt("commonmark").enable("table").render(src)
title = src.splitlines()[0].lstrip("# ").strip()
css = """
@page { size: A4 landscape; margin: 14mm 14mm 16mm 14mm; }
body { font-family: 'Noto Sans', 'Liberation Sans', Arial, sans-serif; font-size: 10pt; line-height: 1.4; color: #1a1a1a; }
h1 { font-size: 20pt; margin: 0 0 6pt; color: #12324a; }
h2 { font-size: 14pt; margin: 16pt 0 6pt; color: #12324a; border-bottom: 1.5pt solid #12324a; padding-bottom: 2pt; page-break-after: avoid; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 10pt; font-size: 8.8pt; }
th { background: #12324a; color: #fff; text-align: left; padding: 4pt 5pt; }
td { border: 0.6pt solid #b8c2cc; padding: 3.5pt 5pt; vertical-align: top; }
tr:nth-child(even) td { background: #f2f5f8; }
tr { page-break-inside: avoid; }
code { font-family: 'Noto Sans Mono', monospace; font-size: 0.92em; background: #eef1f4; padding: 0 2pt; }
a { color: #1d5d8f; text-decoration: none; }
ul { margin: 4pt 0; } li { margin: 2pt 0; }
"""
word = "--word" in sys.argv
if word:  # LibreOffice reads HTML table attributes better than CSS, and needs the fonts on every element
    body = body.replace("<table>", '<table border="1" cellspacing="0" cellpadding="4">')
    css = css.replace("line-height: 1.4", "line-height: 1.15") + "h1, h2, p, td, th, li { font-family: 'Noto Sans', Arial, sans-serif; }"
out = HERE / "export" / (Path(sys.argv[1]).stem + ("-word" if word else "") + ".html")
out.write_text(f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title><style>{css}</style></head><body>{body}</body></html>")
print(out)
