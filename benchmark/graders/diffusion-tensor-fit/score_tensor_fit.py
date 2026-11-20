#!/usr/bin/env python3
"""score_tensor_fit.py — grade FA and MD maps from a diffusion tensor fit, for the
`diffusion-tensor-fit` benchmark task.

The reference is a consensus of a panel of defensible fits of the same acquisition (two
tools, ordinary and weighted least squares, all shells and b <= 1200 only), as their
voxelwise median. Defensible fits differ in level -- the shells used and the estimator move
FA and MD -- far more than in pattern, so the maps are graded mainly on pattern, inside the
reference brain mask eroded away from its edge:

    fa_agreement    Pearson r between the FA map and the consensus FA
    fa_level        median absolute difference between the FA map and the consensus FA
    md_agreement    Pearson r between the MD map and the consensus MD; r ignores scale, so
                    any unit (mm2/s, um2/ms) is read the same

Each metric earns full credit at the line the panel itself reaches (calibrated per subject,
gated) and none at a fixed line from the policy, linearly between. A map of the wrong brain,
a mirrored map or noise sits far below the zero lines.

Validity gates:

    fa_present        output.nii.gz is there and loads as a volume
    geometry_matches  the FA map is on the acquisition's grid: same shape, same affine
    fa_in_range       FA inside the brain lies in [0, 1], but for a few voxels, and is not
                      constant

A missing or unreadable md.nii.gz, or one off the grid, scores md_agreement 0 rather than
failing a gate: FA is the graded file of the output contract, and MD rides along with it.

Pack layout (--pack DIR):
    rubrics/policy.json            weights, zero lines, slack, verdict thresholds
    reference/consensus_fa.nii.gz  the panel's voxelwise median FA
    reference/consensus_md.nii.gz  the panel's voxelwise median MD
    reference/roi_mask.nii.gz      the brain mask the metrics are read in
    reference/rubric.json          written by fetch_reference.py from the policy and the
                                   subject's gated calibration

Usage:
    score_tensor_fit.py --submission SUBMISSION_DIR --pack PACK_DIR [--json out.json]

SUBMISSION_DIR is the case's output directory, `submissions/diffusion-tensor-fit/<case>/`.
Exit code is 0 when the submission is valid (not gate-failed), 1 otherwise.

Dependencies: numpy, nibabel.
"""
import argparse
import json
import sys
from pathlib import Path

import nibabel as nib
import numpy as np

FA, MD = "output.nii.gz", "md.nii.gz"


def rubric_path(pack):
    """The rubric fetch_reference.py merged with the subject's calibration, else the policy."""
    fetched = pack / "reference" / "rubric.json"
    return fetched if fetched.is_file() else pack / "rubrics" / "policy.json"


def load_map(path, notes):
    """A 3-D map as float64 with non-finite values set to 0, and its affine; None if absent."""
    if not path.is_file():
        notes.append(f"no {path.name} in the submission")
        return None, None
    try:
        img = nib.load(str(path))
        data = np.asanyarray(img.dataobj).astype(np.float64)
    except Exception as e:
        notes.append(f"{path.name} could not be read: {type(e).__name__}")
        return None, None
    # a map written as x*y*z*1 is still a 3-D map
    while data.ndim > 3 and data.shape[-1] == 1:
        data = data[..., 0]
    return np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0), img.affine


def on_grid(data, affine, ref_img):
    return (data is not None and data.shape == ref_img.shape[:3]
            and np.allclose(affine, ref_img.affine, atol=1e-3))


def pearson(x, y):
    if x.std() == 0 or y.std() == 0:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def credit_high(value, full, zero):
    """1 at or above `full`, 0 at or below `zero`, linear between."""
    return float(np.clip((value - zero) / (full - zero), 0.0, 1.0))


def credit_low(value, full, zero):
    """1 at or below `full`, 0 at or above `zero`, linear between."""
    return float(np.clip((zero - value) / (zero - full), 0.0, 1.0))


def score(submission_dir, pack_dir):
    pack = Path(pack_dir)
    ref = pack / "reference"
    for f in ("consensus_fa.nii.gz", "consensus_md.nii.gz", "roi_mask.nii.gz"):
        if not (ref / f).is_file():
            raise SystemExit(f"ERROR: no {ref / f}.\nRun: fetch_reference.py --task "
                             f"diffusion-tensor-fit --case <case>")
    rubric = json.loads(rubric_path(pack).read_text())
    cal = rubric.get("calibration")
    if cal is None:
        raise SystemExit(f"ERROR: {rubric_path(pack)} has no calibration; fetch the case's "
                         f"reference with fetch_reference.py, which merges it")
    zero = rubric["zero_lines"]
    ref_img = nib.load(str(ref / "consensus_fa.nii.gz"))
    ref_fa = np.asanyarray(ref_img.dataobj).astype(np.float64)
    ref_md = np.asanyarray(nib.load(str(ref / "consensus_md.nii.gz")).dataobj).astype(np.float64)
    roi = np.asanyarray(nib.load(str(ref / "roi_mask.nii.gz")).dataobj) > 0

    submission = Path(submission_dir)
    notes = []
    fa, fa_aff = load_map(submission / FA, notes)
    md, md_aff = load_map(submission / MD, notes)

    gates = {"fa_present": fa is not None}
    gates["geometry_matches"] = gates["fa_present"] and on_grid(fa, fa_aff, ref_img)
    if gates["fa_present"] and not gates["geometry_matches"]:
        notes.append(f"{FA} is {fa.shape} and not on the acquisition's grid "
                     f"{tuple(ref_img.shape[:3])} with its affine")
    if gates["geometry_matches"]:
        v = fa[roi]
        # A fit writes FA a little above 1 where an eigenvalue comes out negative, in a
        # few voxels; a map on another scale has most of them out of range.
        outside = float(np.mean((v < -1e-6) | (v > 1.0 + 1e-3)))
        gates["fa_in_range"] = bool(outside <= rubric["fa_out_of_range_max"] and v.std() > 0)
        if not gates["fa_in_range"]:
            notes.append(f"FA inside the brain is constant at {v.mean():.3g}" if v.std() == 0
                         else f"{outside:.1%} of FA inside the brain lies outside [0, 1]")
    else:
        gates["fa_in_range"] = False
    failures = [k for k in rubric["gates"] if not gates.get(k, False)]

    metrics, values = {}, {}
    if not failures:
        values["fa_r"] = pearson(fa[roi], ref_fa[roi])
        values["fa_mad"] = float(np.median(np.abs(fa[roi] - ref_fa[roi])))
        metrics["fa_agreement"] = credit_high(values["fa_r"], cal["fa_r_full"], zero["fa_r"])
        metrics["fa_level"] = credit_low(values["fa_mad"], cal["fa_mad_full"], zero["fa_mad"])
        if md is not None and on_grid(md, md_aff, ref_img):
            values["md_r"] = pearson(md[roi], ref_md[roi])
            metrics["md_agreement"] = credit_high(values["md_r"], cal["md_r_full"], zero["md_r"])
        else:
            if md is not None:
                notes.append(f"{MD} is not on the acquisition's grid")
            metrics["md_agreement"] = 0.0

    if failures:
        quality = 0.0
    else:
        w = rubric["weights"]
        quality = 100.0 * sum(w[k] * metrics[k] for k in w) / sum(w.values())

    vt = rubric["verdict_thresholds"]
    if failures:
        verdict = "invalid"
    elif quality >= vt["within_reference_variability"]:
        verdict = "within_reference_variability"
    elif quality >= vt["acceptable"]:
        verdict = "acceptable"
    elif quality >= vt["marginal"]:
        verdict = "marginal"
    else:
        verdict = "unacceptable"

    return {"verdict": verdict, "quality": round(quality, 2),
            "gate_failures": failures, "load_notes": notes,
            "metrics": {k: round(v, 4) for k, v in metrics.items()},
            "values": {k: round(v, 4) for k, v in values.items()}}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--submission", required=True, help="the case's output directory")
    ap.add_argument("--pack", required=True, help="the grader pack")
    ap.add_argument("--json", help="write the result here as well as to stdout")
    a = ap.parse_args()

    res = score(a.submission, a.pack)
    text = json.dumps(res, indent=2) + "\n"
    if a.json:
        Path(a.json).write_text(text)
    sys.stdout.write(text)
    return 1 if res["gate_failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
