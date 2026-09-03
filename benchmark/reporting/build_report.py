#!/usr/bin/env python3
"""Render one benchmark task's grading outputs into a single self-contained HTML report.

Consumes the durable, tiny records the harness emits — `summary.json` (per-cell aggregates +
provenance) and `runs.csv` (one row per run) — which survive an environment purge, plus optional
extras: a grader `rubric.json` (rendered as a scoring card), analysis figures, and per-run QC
thumbnails. Everything is inlined as base64, so the output needs no server and no external asset.

    python build_report.py --summary summary.json --runs runs.csv \
        [--rubric rubric.json] [--figure analysis.png ...] [--thumbs qc/] \
        --title "7T brain extraction" --out report.html

Input schema (summary.json):
    { "task": str, "n_runs": int, "n_valid": int,
      "provenance": {"image_version": {...}, "opencode_version": {...},
                     "skills_sha": {...}, "tasks_sha": {...}},
      "poolable": bool,
      "cells": { "<model>|<arm>": {"n","passes","mean","sd","uptake",
                                   "not_found_claims","methods":{tool:count}} },
      "skill_effect": { "<model>": {"delta_pp","ci95_pp":[lo,hi],"fisher_p", ...} } }

runs.csv must contain at least: model, arm, verdict, score, dice, passed (extra columns are ignored).
"""
import argparse
import base64
import csv
import html
import json
from collections import defaultdict
from pathlib import Path


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def img_tag(path: Path) -> str:
    return f'<img alt="" src="data:image/png;base64,{b64(path.read_bytes())}">'


def one(d: dict) -> str:
    """Collapse a provenance histogram {value: count} to a compact string."""
    if not d:
        return "—"
    return ", ".join(str(k) for k in d)


VERDICT_COLORS = {
    "indistinguishable": "#2ca25f", "acceptable": "#3aa0a0", "marginal": "#d9a441",
    "unacceptable": "#d9784a", "invalid": "#7f8896", "fail": "#7f8896",
}


def verdict_pill(verdict: str) -> str:
    c = VERDICT_COLORS.get(verdict.lower(), "#7f8896")
    return f'<span class="pill" style="--pc:{c}">{html.escape(verdict)}</span>'


def parse_cells(cells: dict):
    """-> (models_in_order, arms_in_order, lookup[(model,arm)])."""
    models, arms = [], []
    lut = {}
    for key, v in cells.items():
        model, _, arm = key.partition("|")
        if model not in models:
            models.append(model)
        if arm not in arms:
            arms.append(arm)
        lut[(model, arm)] = v
    return models, arms, lut


def pass_rate(cell: dict) -> float:
    n = cell.get("n", 0)
    return cell.get("passes", 0) / n if n else 0.0


def leaderboard_table(models, arms, lut, skill_effect, poolable):
    head = "".join(f"<th>{html.escape(a)}<br><span class='sub'>pass · score</span></th>" for a in arms)
    eff = "<th>skill effect</th>" if skill_effect else ""
    rows = []
    for m in models:
        cellhtml = []
        for a in arms:
            c = lut.get((m, a))
            if not c:
                cellhtml.append('<td class="num">—</td>'); continue
            pr = pass_rate(c)
            cellhtml.append(
                f'<td class="num"><b class="pr" style="--v:{pr}">{c["passes"]}/{c["n"]}</b>'
                f'<span class="score"> · {c.get("mean", 0):.0f}±{c.get("sd", 0):.0f}</span></td>')
        e = ""
        if skill_effect and m in skill_effect:
            se = skill_effect[m]
            ci = se.get("ci95_pp", [None, None])
            sig = "sig" if (se.get("fisher_p", 1) or 1) < 0.05 else ""
            e = (f'<td class="num {sig}">{se.get("delta_pp", 0):+.0f} pp'
                 f'<span class="sub"> CI[{ci[0]:.0f},{ci[1]:.0f}] p={se.get("fisher_p", float("nan")):.3f}</span></td>')
        elif skill_effect:
            e = '<td class="num">—</td>'
        rows.append(f"<tr><td><b>{html.escape(m)}</b></td>{''.join(cellhtml)}{e}</tr>")
    # pooled
    if poolable and len(models) > 1:
        pooled = []
        for a in arms:
            tot_p = sum(lut[(m, a)]["passes"] for m in models if (m, a) in lut)
            tot_n = sum(lut[(m, a)]["n"] for m in models if (m, a) in lut)
            pr = tot_p / tot_n if tot_n else 0
            pooled.append(f'<td class="num"><b class="pr" style="--v:{pr}">{tot_p}/{tot_n}</b></td>')
        e = '<td class="num">—</td>' if skill_effect else ""
        rows.append(f'<tr class="pooled"><td><b>ALL</b></td>{"".join(pooled)}{e}</tr>')
    return f"<table><thead><tr><th>model</th>{head}{eff}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def scoring_card(rubric: dict) -> str:
    if not rubric:
        return ""
    gates = "".join(f'<span class="chip">{html.escape(g)}</span>' for g in rubric.get("gates", []))
    weights = rubric.get("weights", {})
    wbars = "".join(
        f'<div class="wrow"><span>{html.escape(k)}</span>'
        f'<span class="wbar"><i style="width:{v*100:.0f}%"></i></span>'
        f'<span class="num">{v:.2f}</span></div>'
        for k, v in sorted(weights.items(), key=lambda kv: -kv[1]))
    vt = rubric.get("verdict_thresholds", {})
    prompt = html.escape(rubric.get("prompt", ""))
    return f"""<section><h2>The task &amp; how it's scored</h2>
      <p class="prompt">{prompt}</p>
      <div class="two">
        <div><h4>Validity gates — any failure ⇒ invalid, score 0</h4>{gates}</div>
        <div><h4>Quality score (weighted, only if gates pass)</h4>{wbars}
          <p class="sub">acceptable ≥ {vt.get('acceptable','?')} · marginal ≥ {vt.get('marginal','?')}</p></div>
      </div></section>"""


def per_run_table(runs):
    cols = ["model", "arm", "verdict", "score", "dice", "passed"]
    have = [c for c in cols if runs and c in runs[0]]
    head = "".join(f"<th>{c}</th>" for c in have)
    rows = []
    for r in runs:
        cells = []
        for c in have:
            val = r.get(c, "")
            if c == "verdict":
                cells.append(f"<td>{verdict_pill(val)}</td>")
            elif c in ("score", "dice"):
                cells.append(f'<td class="num">{val}</td>')
            else:
                cells.append(f"<td>{html.escape(str(val))}</td>")
        rows.append(f"<tr>{''.join(cells)}</tr>")
    return f"<div class='scroll'><table><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"


def gallery(thumbs_dir: Path) -> str:
    if not thumbs_dir or not thumbs_dir.is_dir():
        return ""
    pngs = sorted(thumbs_dir.glob("*.png"))
    if not pngs:
        return ""
    cells = "".join(
        f'<figure class="cell"><img alt="{html.escape(p.stem)}" '
        f'src="data:image/png;base64,{b64(p.read_bytes())}">'
        f'<figcaption>{html.escape(p.stem)}</figcaption></figure>' for p in pngs)
    return f"<section><h2>Run snapshot</h2><div class='grid'>{cells}</div></section>"


STYLE = """<style>
:root{--bg:#f5f8fb;--panel:#fff;--ink:#16222e;--muted:#5b6b7a;--line:#e0e8ef;--accent:#2c7fb8;
--accent-soft:#e7f1f8;--mono:ui-monospace,Menlo,Consolas,monospace;
--sans:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;
--shadow:0 1px 2px rgba(20,40,60,.06),0 8px 24px rgba(20,40,60,.05)}
@media(prefers-color-scheme:dark){:root{--bg:#0e1620;--panel:#16212e;--ink:#dce6ef;--muted:#8ea0b2;
--line:#26333f;--accent:#4aa3d6;--accent-soft:#16303f;--shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35)}}
:root[data-theme=light]{--bg:#f5f8fb;--panel:#fff;--ink:#16222e;--muted:#5b6b7a;--line:#e0e8ef;--accent:#2c7fb8;--accent-soft:#e7f1f8}
:root[data-theme=dark]{--bg:#0e1620;--panel:#16212e;--ink:#dce6ef;--muted:#8ea0b2;--line:#26333f;--accent:#4aa3d6;--accent-soft:#16303f}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.55}
.wrap{max-width:1080px;margin:0 auto;padding:40px 24px 80px}h1{font-size:1.8rem;margin:0 0 4px;letter-spacing:-.02em}
h2{font-size:1.12rem;margin:0 0 14px}h4{font-size:.8rem;color:var(--muted);margin:0 0 8px;font-weight:600}
.sub{color:var(--muted);font-size:.82em}.chips{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 26px}
.provchip{font:600 12px/1 var(--mono);background:var(--panel);border:1px solid var(--line);color:var(--muted);padding:7px 10px;border-radius:7px}
.provchip b{color:var(--ink)}
section{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:22px 24px;margin:0 0 22px;box-shadow:var(--shadow)}
.two{display:grid;grid-template-columns:1.3fr 1fr;gap:24px}@media(max-width:720px){.two{grid-template-columns:1fr}}
.prompt{background:var(--accent-soft);border-left:3px solid var(--accent);padding:12px 16px;border-radius:0 8px 8px 0;margin:0 0 14px}
.chip{display:inline-block;font:600 11px/1 var(--mono);background:var(--bg);border:1px solid var(--line);padding:5px 8px;border-radius:6px;margin:0 5px 6px 0;color:var(--muted)}
.wrow{display:grid;grid-template-columns:120px 1fr 40px;gap:10px;align-items:center;margin:6px 0;font-size:.85rem}
.wbar{height:8px;background:var(--bg);border:1px solid var(--line);border-radius:5px;overflow:hidden}.wbar i{display:block;height:100%;background:var(--accent)}
table{width:100%;border-collapse:collapse;font-size:.88rem}.scroll{overflow-x:auto}
th{text-align:left;font-size:.72rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);font-weight:600;padding:0 12px 10px;border-bottom:1px solid var(--line)}
td{padding:9px 12px;border-bottom:1px solid var(--line)}tr:last-child td{border-bottom:none}
.num{font-variant-numeric:tabular-nums;font-family:var(--mono);text-align:right;white-space:nowrap}
tr.pooled td{border-top:2px solid var(--line);font-weight:700}
.pr{padding:2px 7px;border-radius:5px;color:#fff;background:color-mix(in srgb,#2ca25f calc(var(--v)*100%),#c14a3a)}
.score{color:var(--muted);font-size:.85em}.sig{color:#2ca25f}
.pill{display:inline-block;font:600 11px/1 var(--sans);color:#fff;background:var(--pc);padding:4px 8px;border-radius:20px}
figure.fig{margin:0 0 16px}figure.fig img{width:100%;border-radius:10px;border:1px solid var(--line);display:block}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(92px,1fr));gap:9px}
.cell{margin:0;border:1px solid var(--line);border-radius:8px;overflow:hidden;background:#000}.cell img{width:100%;display:block}
.cell figcaption{background:var(--panel);color:var(--muted);font:600 10px var(--mono);padding:3px 5px;text-align:center}
footer{color:var(--muted);font-size:.8rem;line-height:1.7}footer code{font-family:var(--mono);background:var(--panel);border:1px solid var(--line);border-radius:4px;padding:1px 5px}
</style>"""


def build(summary, runs, rubric, figures, thumbs, title):
    models, arms, lut = parse_cells(summary.get("cells", {}))
    prov = summary.get("provenance", {})
    chips = [
        f'<span class="provchip">task <b>{html.escape(summary.get("task", "—"))}</b></span>',
        f'<span class="provchip">runs <b>{summary.get("n_runs", len(runs))}</b></span>',
    ]
    for label, key in (("image", "image_version"), ("opencode", "opencode_version"),
                       ("skills", "skills_sha"), ("task", "tasks_sha")):
        if prov.get(key):
            chips.append(f'<span class="provchip">{label} <b>{html.escape(one(prov[key]))}</b></span>')

    figs = "".join(f'<figure class="fig">{img_tag(f)}</figure>' for f in figures if f.exists())
    fig_section = f"<section><h2>Analysis</h2>{figs}</section>" if figs else ""

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>
{STYLE}</head><body><div class="wrap">
  <h1>{html.escape(title)}</h1>
  <div class="chips">{''.join(chips)}</div>
  {scoring_card(rubric)}
  <section><h2>Leaderboard</h2>{leaderboard_table(models, arms, lut, summary.get("skill_effect"), summary.get("poolable"))}
    <p class="sub">pass = valid &amp; verdict ≥ acceptable · score is mean quality (0–100) ± sd</p></section>
  {fig_section}
  {gallery(thumbs)}
  <section><h2>All runs</h2>{per_run_table(runs)}</section>
  <footer>Generated by <code>build_report.py</code> from the harness <code>summary.json</code> / <code>runs.csv</code>.
  Self-contained: every asset is inlined, so this file is portable and needs no server.</footer>
</div></body></html>"""


def main():
    ap = argparse.ArgumentParser(description="Render a task's grading outputs into a self-contained HTML report.")
    ap.add_argument("--summary", required=True, type=Path)
    ap.add_argument("--runs", required=True, type=Path)
    ap.add_argument("--rubric", type=Path)
    ap.add_argument("--figure", type=Path, action="append", default=[], help="analysis figure(s) to embed")
    ap.add_argument("--thumbs", type=Path, help="dir of per-run QC PNGs for the gallery (optional)")
    ap.add_argument("--title", default="Benchmark report")
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()

    summary = json.load(open(a.summary))
    runs = list(csv.DictReader(open(a.runs)))
    rubric = json.load(open(a.rubric)) if a.rubric else None
    a.out.write_text(build(summary, runs, rubric, a.figure, a.thumbs, a.title))
    print(f"wrote {a.out} ({a.out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
