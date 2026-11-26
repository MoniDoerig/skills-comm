#!/usr/bin/env python3
"""score_task_glm.py — grade the z maps of a first-level task GLM, for the
`functional-task-glm` benchmark task.

The task asks for six contrasts of the finger-foot-lips paradigm: each movement against
rest (finger, foot, lips) and each movement against the mean of the other two
(finger_vs_others, foot_vs_others, lips_vs_others). The reference is a consensus of a panel
of independent first-level GLMs of the same preprocessed BOLD (four packages, each at its
own conventions for smoothing, HRF, drift and noise model), as the voxelwise median z map
per contrast. Defensible GLMs differ in smoothness and scale far more than in where the
activation lies, so each map is graded on its pattern, inside the BOLD brain mask:

    <contrast>   Pearson r between the submitted map and the consensus map

r reads any monotone scale alike for pattern, so a t map or an effect-size map is read as a
z map would be. Each contrast earns full credit at the line the panel itself reaches
(calibrated per subject, gated) and none at a fixed line from the policy, linearly
between. The movement-vs-others maps carry most weight: they hold the somatotopy, while
the three movement-vs-rest maps share most of their pattern.

Validity gates:

    maps_present        the three movement-vs-others maps are there and load as volumes
    geometry_matches    they are on the BOLD grid: same shape, same affine
    maps_vary           none is constant inside the brain
    contrast_identity   each movement-vs-others map agrees best with its own consensus,
                        not with another movement's: conditions labelled wrongly, or maps
                        written under each other's names, fail here

A missing or unreadable movement-vs-rest map, or one off the grid, scores 0 for that
contrast rather than failing a gate.

Pack layout (--pack DIR):
    rubrics/policy.json                  weights, zero lines, slack, verdict thresholds
    reference/consensus_z_<c>.nii.gz     the panel's voxelwise median z map, per contrast
    reference/roi_mask.nii.gz            the brain mask the metrics are read in
    reference/rubric.json                written by fetch_reference.py from the policy and
                                         the subject's gated calibration

Usage:
    score_task_glm.py --submission SUBMISSION_DIR --pack PACK_DIR [--json out.json]

SUBMISSION_DIR is the case's output directory, `submissions/functional-task-glm/<case>/`,
holding z_<contrast>.nii.gz for each contrast. Exit code is 0 when the submission is valid
(not gate-failed), 1 otherwise.

Dependencies: numpy, nibabel.
"""
import argparse
import json
import sys
from pathlib import Path

import nibabel as nib
import numpy as np

SPECIFIC = ["finger_vs_others", "foot_vs_others", "lips_vs_others"]
VS_REST = ["finger", "foot", "lips"]
CONTRASTS = SPECIFIC + VS_REST


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


def score(submission_dir, pack_dir):
    pack = Path(pack_dir)
    ref = pack / "reference"
    for f in [f"consensus_z_{c}.nii.gz" for c in CONTRASTS] + ["roi_mask.nii.gz"]:
        if not (ref / f).is_file():
            raise SystemExit(f"ERROR: no {ref / f}.\nRun: fetch_reference.py --task "
                             f"functional-task-glm --case <case>")
    rubric = json.loads(rubric_path(pack).read_text())
    cal = rubric.get("calibration")
    if cal is None:
        raise SystemExit(f"ERROR: {rubric_path(pack)} has no calibration; fetch the case's "
                         f"reference with fetch_reference.py, which merges it")
    roi_img = nib.load(str(ref / "roi_mask.nii.gz"))
    roi = np.asanyarray(roi_img.dataobj) > 0
    cons = {c: np.asanyarray(nib.load(str(ref / f"consensus_z_{c}.nii.gz")).dataobj)
            .astype(np.float64)[roi] for c in CONTRASTS}

    submission = Path(submission_dir)
    notes = []
    maps, ok = {}, {}
    for c in CONTRASTS:
        data, aff = load_map(submission / f"z_{c}.nii.gz", notes)
        ok[c] = on_grid(data, aff, roi_img)
        if data is not None and not ok[c]:
            notes.append(f"z_{c}.nii.gz is {data.shape} and not on the BOLD grid "
                         f"{tuple(roi_img.shape[:3])} with its affine")
        maps[c] = data[roi] if ok[c] else None

    gates = {"maps_present": all(maps[c] is not None or (submission / f"z_{c}.nii.gz").is_file()
                                 for c in SPECIFIC)}
    gates["geometry_matches"] = all(ok[c] for c in SPECIFIC)
    gates["maps_vary"] = gates["geometry_matches"] and all(maps[c].std() > 0 for c in SPECIFIC)
    if gates["geometry_matches"] and not gates["maps_vary"]:
        notes.append("constant inside the brain: " +
                     ", ".join(f"z_{c}" for c in SPECIFIC if maps[c].std() == 0))
    values = {}
    if gates["maps_vary"]:
        # each specific map against every specific consensus: it must agree best with its own
        cross = {c: {k: pearson(maps[c], cons[k]) for k in SPECIFIC} for c in SPECIFIC}
        swapped = [c for c in SPECIFIC if max(cross[c], key=cross[c].get) != c]
        gates["contrast_identity"] = not swapped
        if swapped:
            notes.append("agrees best with another movement's consensus: " + ", ".join(
                f"z_{c} -> {max(cross[c], key=cross[c].get)}" for c in swapped))
        values.update({f"r_{c}": cross[c][c] for c in SPECIFIC})
    else:
        gates["contrast_identity"] = False
    failures = [k for k in rubric["gates"] if not gates.get(k, False)]

    metrics = {}
    if not failures:
        zero = rubric["zero_lines"]
        for c in CONTRASTS:
            if maps[c] is None:
                metrics[c] = 0.0
                continue
            r = values.get(f"r_{c}", pearson(maps[c], cons[c]))
            values[f"r_{c}"] = r
            kind = "vs_others" if c in SPECIFIC else "vs_rest"
            metrics[c] = credit_high(r, cal["r_full"][c], zero[kind])

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
