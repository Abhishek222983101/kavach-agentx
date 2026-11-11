"""Regenerate docs/diagrams/architecture.html from the mermaid blocks in SYSTEM-ARCHITECTURE.md."""
import html, re, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
md = (root / "docs/03-SYSTEM/SYSTEM-ARCHITECTURE.md").read_text()
blocks = re.findall(r"### (8\.\d [^\n]+)\n```mermaid\n(.*?)```", md, re.S)
parts = "".join(f'<section><h2>{html.escape(t)}</h2><pre class="mermaid">{html.escape(b)}</pre></section>' for t, b in blocks)
page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kavach Architecture</title><style>
:root{{--bg:#fafaf7;--fg:#151515;--card:#fff;--line:#e3e3dc}}
@media (prefers-color-scheme:dark){{:root{{--bg:#111;--fg:#eee;--card:#1b1b1b;--line:#333}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif}}
main{{max-width:1200px;margin:auto;padding:16px}} section{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin:16px 0;overflow-x:auto}}
</style></head><body><main><h1>Kavach: system diagrams</h1><p>Generated from docs/03-SYSTEM/SYSTEM-ARCHITECTURE.md §8 by scripts/build_diagrams.py.</p>{parts}</main>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
<script>mermaid.initialize({{startOnLoad:true,theme:matchMedia('(prefers-color-scheme: dark)').matches?'dark':'default'}});</script></body></html>"""
(root / "docs/diagrams/architecture.html").write_text(page)
print(f"{len(blocks)} diagrams written")
