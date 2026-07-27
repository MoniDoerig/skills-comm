#!/usr/bin/env python3
"""registration_qc.py — orchestrate registration QC with validated binaries.

This is GLUE, not a metric implementation. It calls validated tools
(ANTs CreateJacobianDeterminantImage / MeasureImageSimilarity /
LabelOverlapMeasures, FSL fslstats, c3d) via subprocess, parses their output,
renders the visuals, writes a metrics row, and — across a cohort — flags
outliers with the median/MAD modified z-score. It does NOT compute Dice, MI, or
the Jacobian in Python, and it does NOT decide the verdict (a human/agent applies
references/rubric.md). Keep this file as the reproducibility record.

Usage:
  registration_qc.py --fixed F --moving-warped W --outdir D --subject ID \
    [--warp WARP] [--moving-labels ML --ref-labels RL] [--mask M] \
    [--mode same|cross] [--timestamp TS] [--cohort-csv path]

Required: --fixed, --moving-warped, --outdir, --subject
The --cohort-csv accumulates one row per run; when it holds >= 5 rows the script
reports modified-z outliers per metric (|z| > 3.5, Iglewicz-Hoaglin) for triage.
"""
import argparse
import csv
import datetime as dt
import os
import re
import shutil
import statistics
import subprocess
import sys


def have(binary):
    return shutil.which(binary) is not None


def require(binary):
    if not have(binary):
        sys.exit(f"ERROR: '{binary}' not on PATH — load its module before running")


def run(cmd):
    """Run a command, return stripped stdout. Raises on non-zero exit."""
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return out.stdout.strip()


def try_run(cmd, what):
    """Run a non-critical command (e.g. a visual); warn but don't abort."""
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except Exception as e:  # noqa: BLE001
        print(f"WARNING: {what} failed ({e})")
        return False


def last_float(text):
    nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", text)
    return float(nums[-1]) if nums else None


def jacobian_metrics(warp, prefix, mask):
    """Returns dict; numbers come from ANTs/FSL/c3d, parsed here."""
    require("CreateJacobianDeterminantImage")
    require("fslstats")
    jac = f"{prefix}_jac.nii.gz"
    logjac = f"{prefix}_logjac.nii.gz"
    run(["CreateJacobianDeterminantImage", "3", warp, jac, "0", "0"])
    run(["CreateJacobianDeterminantImage", "3", warp, logjac, "1", "0"])
    rng = run(["fslstats", jac, "-R"]).split()
    jmin, jmax = float(rng[0]), float(rng[1])
    sd_cmd = ["fslstats", logjac] + (["-k", mask] if mask else []) + ["-s"]
    logjac_sd = float(run(sd_cmd))
    fold_pct = None
    if have("c3d"):
        fold = last_float(run(["c3d", jac, "-thresh", "-inf", "0", "1", "0", "-voxel-sum"]))
        tot = float(run(["fslstats", jac, "-V"]).split()[0])
        fold_pct = round(100.0 * fold / tot, 4) if tot > 0 else None
    return {
        "jac_min": jmin, "jac_max": jmax, "logjac_sd": round(logjac_sd, 4),
        "folding_pct": fold_pct, "folding": "YES" if jmin <= 0 else "no",
        "_jac_png_src": jac,
    }


def similarity(fixed, warped, mode, mask):
    require("MeasureImageSimilarity")
    metric = (f"MI[{fixed},{warped},1,32]" if mode == "cross"
              else f"CC[{fixed},{warped},1,4]")
    cmd = ["MeasureImageSimilarity", "-d", "3", "-m", metric]
    if mask:
        cmd += ["-x", mask]
    return last_float(run(cmd)), metric


def overlap(moving_labels, ref_labels, prefix):
    require("LabelOverlapMeasures")
    csv_path = f"{prefix}_overlap.csv"
    run(["LabelOverlapMeasures", "3", moving_labels, ref_labels, csv_path])
    dices = {}
    with open(csv_path) as fh:
        reader = csv.reader(fh)
        header = next(reader, None)
        # cols: Label,Total,Jaccard,Dice,... ; keep labels > 0
        for row in reader:
            if len(row) < 4:
                continue
            try:
                label, dice = int(float(row[0])), float(row[3])
            except ValueError:
                continue
            if label > 0:
                dices[label] = dice
    if not dices:
        return {"mean_dice": None, "worst_roi": None, "worst_dice": None, "_csv": csv_path}
    worst_roi = min(dices, key=dices.get)
    return {"mean_dice": round(sum(dices.values()) / len(dices), 4),
            "worst_roi": worst_roi, "worst_dice": round(dices[worst_roi], 4),
            "_csv": csv_path}


def render_visuals(fixed, warped, prefix, has_warp):
    edge, jacpng, mosaic = f"{prefix}_edge.png", f"{prefix}_jac.png", f"{prefix}_mosaic.png"
    if have("fsleyes"):
        try_run(["fsleyes", "render", "--outfile", edge, warped, fixed,
                 "-ot", "edge", "-lw", "2", "-cm", "red"], "edge overlay")
        if has_warp:
            try_run(["fsleyes", "render", "--outfile", jacpng, fixed,
                     f"{prefix}_jac.nii.gz", "-cm", "brain_colours_diverging",
                     "-dr", "0", "2", "-a", "60"], "jacobian heatmap")
    elif have("slices"):
        try_run(["slices", warped, fixed, "-o", edge], "slices edge overlay")
    if have("CreateTiledMosaic") and have("ConvertScalarImageToRGB"):
        if try_run(["ConvertScalarImageToRGB", "3", warped, f"{prefix}_rgb.nii.gz",
                    "none", "hot"], "rgb convert"):
            try_run(["CreateTiledMosaic", "-i", fixed, "-r", f"{prefix}_rgb.nii.gz",
                     "-o", mosaic, "-a", "0.35", "-t", "-1x-1", "-d", "2"], "mosaic")
    return [p for p in (edge, jacpng if has_warp else None, mosaic) if p]


def append_cohort(cohort_csv, row):
    fields = ["subject", "timestamp", "mode", "folding_pct", "jac_min", "jac_max",
              "logjac_sd", "similarity", "mean_dice", "worst_dice"]
    exists = os.path.exists(cohort_csv)
    with open(cohort_csv, "a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def flag_outliers(cohort_csv):
    """Modified z-score per metric across the cohort; |z|>3.5 flagged.

    Iglewicz-Hoaglin: z = 0.6745*(x-median)/MAD, with the documented meanAD
    fallback (z = (x-median)/(1.2533*meanAD)) when MAD == 0, and no flags when
    the cohort is constant (meanAD == 0 too).
    """
    with open(cohort_csv) as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) < 5:
        print(f"Cohort has {len(rows)} rows (<5) — skipping outlier flagging.")
        return
    print(f"\nCohort outlier check ({len(rows)} subjects, modified-z |>3.5|):")
    for metric in ("folding_pct", "logjac_sd", "similarity", "mean_dice"):
        vals = [(r["subject"], float(r[metric])) for r in rows
                if r.get(metric) not in (None, "", "None")]
        if len(vals) < 5:
            continue
        xs = [v for _, v in vals]
        med = statistics.median(xs)
        devs = [abs(x - med) for x in xs]
        mad = statistics.median(devs)
        if mad > 0:
            def z(x, mad=mad):
                return 0.6745 * (x - med) / mad
        else:
            mean_ad = sum(devs) / len(devs)
            if mean_ad == 0:
                print(f"  [{metric}] constant across cohort — no outliers")
                continue
            def z(x, mean_ad=mean_ad):
                return (x - med) / (1.253314 * mean_ad)
        flagged = [(s, x, z(x)) for s, x in vals if abs(z(x)) > 3.5]
        if flagged:
            for s, x, zv in flagged:
                print(f"  [{metric}] {s}: {x} (z={zv:+.1f})")
        else:
            print(f"  [{metric}] no outliers")


def write_report(path, subject, fixed, warped, mode, jac, sim, metric, ov, visuals):
    fold = jac.get("folding_pct", "n/a")
    folding = jac.get("folding", "unknown")
    md = f"""## Registration QC — {subject} ({warped} → {fixed})

**Verdict: <PASS | BORDERLINE | FAIL>  ·  Confidence: <HIGH | MEDIUM | LOW>**

### Quantitative
| Metric | Value | Reference / cohort |
|--------|-------|--------------------|
| Folding (Jacobian ≤0) | {fold}% | 0% required |
| Jacobian min / max | {jac.get('jac_min','n/a')} / {jac.get('jac_max','n/a')} | strictly positive |
| log-Jacobian SD | {jac.get('logjac_sd','n/a')} | vs cohort |
| Similarity ({mode}) | {sim} | expected range / cohort |
| Mean Dice | {ov.get('mean_dice','n/a')} | size-dependent |
| Worst ROI Dice | {ov.get('worst_roi','n/a')}={ov.get('worst_dice','n/a')} | flag if collapsed |

### Criteria  (rate per references/rubric.md; folding={folding} is a HARD-STOP if YES)
| Criterion | Rating | Notes |
|-----------|--------|-------|
| 1. Boundary / structural correspondence | <> | edge overlay |
| 2. Deformation regularity (no folding) | <> | folding={folding} |
| 3. Label / tissue overlap | <> | meanDice={ov.get('mean_dice','n/a')} |
| 4. Intensity similarity | <> | {sim} |
| 5. Global alignment / no gross error | <> | check space/orientation/swap |

### Reasoning
<which criteria drove the verdict; dominant concern; why this confidence>

### Visuals
{chr(10).join(visuals)}

### Recommendation
<use as-is / use with caution in region X / re-run with changes Y / manual review>
"""
    with open(path, "w") as fh:
        fh.write(md)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixed", required=True)
    ap.add_argument("--moving-warped", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--warp")
    ap.add_argument("--moving-labels")
    ap.add_argument("--ref-labels")
    ap.add_argument("--mask")
    ap.add_argument("--mode", choices=["same", "cross"], default="same")
    ap.add_argument("--timestamp", default=dt.datetime.now().strftime("%Y%m%d-%H%M%S"))
    ap.add_argument("--cohort-csv")
    a = ap.parse_args()

    qc = os.path.join(a.outdir, "qc")
    os.makedirs(qc, exist_ok=True)
    prefix = os.path.join(qc, f"{a.subject}_{a.timestamp}")

    jac = {}
    if a.warp:
        jac = jacobian_metrics(a.warp, prefix, a.mask)
    else:
        print("Jacobian SKIPPED (no --warp) — folding/regularity not assessable")

    sim, metric = similarity(a.fixed, a.moving_warped, a.mode, a.mask)

    ov = {}
    if a.moving_labels and a.ref_labels:
        ov = overlap(a.moving_labels, a.ref_labels, prefix)
    else:
        print("Overlap SKIPPED (need --moving-labels and --ref-labels in target space)")

    visuals = render_visuals(a.fixed, a.moving_warped, prefix, bool(a.warp))

    report = f"{prefix}_ai_eval.md"
    write_report(report, a.subject, a.fixed, a.moving_warped, a.mode,
                 jac, sim, metric, ov, visuals)

    row = {"subject": a.subject, "timestamp": a.timestamp, "mode": a.mode,
           "folding_pct": jac.get("folding_pct"), "jac_min": jac.get("jac_min"),
           "jac_max": jac.get("jac_max"), "logjac_sd": jac.get("logjac_sd"),
           "similarity": sim, "mean_dice": ov.get("mean_dice"),
           "worst_dice": ov.get("worst_dice")}
    print("Metrics:", {k: v for k, v in row.items() if v is not None})
    print("Report scaffold:", report, "(fill criteria/verdict via references/rubric.md)")

    if a.cohort_csv:
        append_cohort(a.cohort_csv, row)
        flag_outliers(a.cohort_csv)


if __name__ == "__main__":
    main()
