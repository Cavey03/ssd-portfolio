# CLAUDE.md – tools/summaries

Workspace-wide rules are in `~/Projects/CLAUDE.md`. Claude loads that file too.

## What this is
The generator for the ITRI626 study-summary pages: one `<unit>/SU<n>-summary.html` per study unit and the
combined `summary-all.html` at the root.

## Rules
- Edit `content.py` (the text) or `build.py` (layout and styles), then run `python3 tools/summaries/build.py`.
  **Never hand-edit the generated HTML**: the next build overwrites it.
- Source: Trask's *Grokking Deep Learning* (PDF in `~/Downloads`). **Never commit the PDF.** Anything not in
  the book is marked "Not in Trask".
