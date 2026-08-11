#!/usr/bin/env python3
"""Build the leaderboard overview: a task × model grid where each task links to its full report.

Reads one `summary.json` per task (the harness output) and emits a single self-contained
`index.html`. Each cell shows a model's pass rate; when a task has two arms (e.g. no-skill vs
with-skill) both are shown. Tasks with a `report_href` become clickable.

    python build_index.py \
        --entry "brain-extraction-7t" path/to/summary.json report_7t.html \
        --entry "tissue-seg-7t"       path/to/summary2.json ./report_tissue.html \
        --out index.html

`report_href` may be a relative path (committed alongside index.html) or a URL.
"""
import argparse
import html
import json
from pathlib import Path


ARM_LABEL = {"env-only": "no skill", "env+skill": "with skill",
             "baseline": "no skill", "skill": "with skill"}


def cell_matrix(summary):
    """summary.json -> {model: {arm: (passes, n)}}, preserving model order."""
    out = {}
    for key, v in summary.get("cells", {}).items():
        model, _, arm = key.partition("|")
        out.setdefault(model, {})[arm] = (v.get("passes", 0), v.get("n", 0))
    return out


def pct_badge(passes, n):
    r = passes / n if n else 0
    return f'<span class="pct" style="--v:{r}">{r*100:.0f}%</span>'


STYLE = """<style>
:root{--bg:#f5f8fb;--panel:#fff;--ink:#16222e;--muted:#5b6b7a;--line:#e0e8ef;--accent:#2c7fb8;
--accent-soft:#e7f1f8;--pend:#aeb9c4;--base:#7fa8c9;--skill:#2ca25f;
--mono:ui-monospace,Menlo,Consolas,monospace;--sans:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;
--shadow:0 1px 2px rgba(20,40,60,.06),0 10px 30px rgba(20,40,60,.05)}
@media(prefers-color-scheme:dark){:root{--bg:#0e1620;--panel:#16212e;--ink:#dce6ef;--muted:#8ea0b2;--line:#26333f;
--accent:#4aa3d6;--accent-soft:#16303f;--pend:#3a4756;--base:#6f98ba;--skill:#3cb371;--shadow:0 1px 2px rgba(0,0,0,.3),0 12px 32px rgba(0,0,0,.4)}}
:root[data-theme=light]{--bg:#f5f8fb;--panel:#fff;--ink:#16222e;--muted:#5b6b7a;--line:#e0e8ef;--accent:#2c7fb8;--base:#7fa8c9;--skill:#2ca25f}
:root[data-theme=dark]{--bg:#0e1620;--panel:#16212e;--ink:#dce6ef;--muted:#8ea0b2;--line:#26333f;--accent:#4aa3d6;--base:#6f98ba;--skill:#3cb371}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15px}
.wrap{max-width:960px;margin:0 auto;padding:44px 22px 70px}h1{font-size:1.7rem;margin:0 0 4px}.sub{color:var(--muted);margin:0 0 20px}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:.8rem;color:var(--muted);margin-bottom:14px;align-items:center}
.legend .sw{width:11px;height:11px;border-radius:3px;display:inline-block;vertical-align:middle;margin-right:5px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow);overflow:hidden}
.scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:.9rem;min-width:640px}
th{font-size:.72rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);font-weight:600;text-align:center;padding:16px 12px 12px;border-bottom:1px solid var(--line)}
th.task{text-align:left}th .model{font-family:var(--mono);text-transform:none;font-size:.82rem;color:var(--ink)}
td{padding:12px;border-bottom:1px solid var(--line);text-align:center;vertical-align:middle}tr:last-child td{border-bottom:none}
tr:hover td{background:color-mix(in srgb,var(--accent-soft) 55%,transparent)}
.task a{color:var(--ink);text-decoration:none;font-weight:600}.task a:hover{color:var(--accent)}
.task span.na{color:var(--muted);font-weight:400}
.cell{display:inline-flex;flex-direction:column;gap:5px;min-width:104px}
.row{display:flex;align-items:center;justify-content:space-between;gap:8px}
.clab{font:600 10px/1 var(--mono);padding:3px 6px;border-radius:5px;color:#fff}.clab.base{background:var(--base)}.clab.skill{background:var(--skill)}
.pct{font:700 12px/1 var(--sans);color:#fff;padding:4px 8px;border-radius:20px;min-width:44px;text-align:center;font-variant-numeric:tabular-nums;background:color-mix(in srgb,#2ca25f calc(var(--v)*100%),#c14a3a)}
.foot{color:var(--muted);font-size:.8rem;margin-top:18px}.foot code{font-family:var(--mono);background:var(--panel);border:1px solid var(--line);border-radius:4px;padding:1px 5px}
</style>"""


def build(entries):
    # entries: list of (task_name, summary_dict, report_href)
    models = []
    for _, s, _ in entries:
        for m in cell_matrix(s):
            if m not in models:
                models.append(m)

    head = "".join(f'<th><span class="model">{html.escape(m)}</span></th>' for m in models)
    rows = []
    for name, s, href in entries:
        mat = cell_matrix(s)
        tds = []
        for m in models:
            arms = mat.get(m)
            if not arms:
                tds.append('<td><span class="na">—</span></td>'); continue
            lines = []
            for arm, (p, n) in arms.items():
                lab = ARM_LABEL.get(arm, arm)
                cls = "skill" if "skill" in arm and "only" not in arm else "base"
                lines.append(f'<span class="row"><span class="clab {cls}">{html.escape(lab)}</span>{pct_badge(p, n)}</span>')
            tds.append(f'<td><span class="cell">{"".join(lines)}</span></td>')
        label = html.escape(name)
        tcell = f'<a href="{html.escape(href)}">{label}</a>' if href else label
        rows.append(f'<tr><td class="task">{tcell}</td>{"".join(tds)}</tr>')

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Benchmark leaderboard</title>
{STYLE}</head><body><div class="wrap">
  <h1>Neurodesk agent benchmark — leaderboard</h1>
  <p class="sub">Pass rate per model on each task. Click a task for its full report.</p>
  <div class="legend"><span><span class="sw" style="background:var(--base)"></span>no skill</span>
    <span><span class="sw" style="background:var(--skill)"></span>with skill</span>
    <span>pass = valid &amp; verdict ≥ acceptable</span></div>
  <div class="card scroll"><table><thead><tr><th class="task">Task</th>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>
  <p class="foot">Generated by <code>build_index.py</code> from each task's <code>summary.json</code>.</p>
</div></body></html>"""


def main():
    ap = argparse.ArgumentParser(description="Build the task × model leaderboard index.")
    ap.add_argument("--entry", nargs=3, action="append", metavar=("NAME", "SUMMARY_JSON", "REPORT_HREF"),
                    required=True, help="repeatable: one task entry (use '' for no report link)")
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    entries = [(name, json.load(open(sj)), href) for name, sj, href in a.entry]
    a.out.write_text(build(entries))
    print(f"wrote {a.out} ({a.out.stat().st_size // 1024} KB, {len(entries)} task(s))")


if __name__ == "__main__":
    main()
