#!/usr/bin/env python3
"""score_registration.py — grade a T1w-to-MNI registration for the
`structural-mni-registration` benchmark task.

This is the GRADER-side scorer, not an agent-facing skill.

Why not image similarity alone: correlation between a warped T1w and the template is dominated
by gross head position and is nearly saturated once any affine has been applied, so it barely
separates an affine from a nonlinear warp. The sensitive measurement is **label propagation** —
carry the subject's own tissue segmentation through the same transform and ask where the tissue
landed. That is the standard way registration is evaluated, and it is tool-agnostic: every
registration package can apply its own transform to a second image.

The reference is not another tool's warp. It is the **template's own tissue priors**, which state
where CSF, grey matter and white matter belong in MNI space independently of any registration
software. A population prior is not a per-subject truth, so the thresholds are not absolute:
`rubric.json` carries the envelope actually achieved by a panel of accepted nonlinear
registrations on this subject (see PROVENANCE.md), and scoring is relative to that.

Pack layout (--pack DIR):
    rubric.json                          calibrated numbers (envelope, weights, gates, grid)
    reference/template_T1w.nii.gz        MNI152NLin2009cAsym T1w
    reference/template_brain_mask.nii.gz
    reference/template_probseg_CSF.nii.gz, _GM.nii.gz, _WM.nii.gz

Usage:
    score_registration.py --warped agent_T1w_in_mni.nii.gz --dseg agent_dseg_in_mni.nii.gz \
        --pack PACK_DIR [--json out.json]

Exit 0 when valid (verdict != invalid), 1 otherwise. Deps: numpy, scipy, nibabel.
"""
import argparse
import json
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

STRUCT = ndi.generate_binary_structure(3, 1)
# Label convention of the segmentation the task hands the agent. Verified from the data rather
# than assumed: on the subject's T1w the mean intensity per label is WM > GM > CSF, which fixes
# the mapping as 1=GM, 2=WM, 3=CSF. rubric.json carries it so the scorer never guesses.
TISSUES = {"GM": 1, "WM": 2, "CSF": 3}
LOWER_BETTER = {"abs_brain_volume_err_pct"}


def same_grid(a, b, tol=1e-3):
    return a.shape[:3] == b.shape[:3] and np.allclose(a.affine, b.affine, atol=tol)


def load_on_grid(path, ref_img, label=False):
    """Load a submission on the reference grid.

    Returns (data, notes, nonfinite). NiftyReg and some other resamplers write NaN outside the
    field of view rather than zero, which is a convention rather than a defect, so non-finite
    values are zeroed here and judged later against the brain mask: NaN in the background is
    fine, NaN inside the brain is not.
    """
    raw = nib.load(str(path))
    img = nib.as_closest_canonical(raw)
    data = np.asanyarray(img.dataobj).astype(np.float64)
    notes = []
    nonfinite = ~np.isfinite(data)
    if nonfinite.any():
        notes.append(f"non_finite_zeroed({int(nonfinite.sum())})")
        data = np.nan_to_num(data)
    if not same_grid(img, ref_img):
        notes.append(f"grid_mismatch{tuple(img.shape[:3])}")
        order = 0 if label else 1
        xfm = np.linalg.inv(img.affine) @ ref_img.affine
        data = ndi.affine_transform(data, xfm[:3, :3], offset=xfm[:3, 3],
                                    output_shape=ref_img.shape[:3], order=order,
                                    mode="constant", cval=0)
        nonfinite = ndi.affine_transform(nonfinite.astype(np.uint8), xfm[:3, :3],
                                         offset=xfm[:3, 3], output_shape=ref_img.shape[:3],
                                         order=0, mode="constant", cval=0) > 0
        notes.append("resampled")
    return data, notes, nonfinite


def dice(a, b):
    s = a.sum() + b.sum()
    return float(2 * (a & b).sum() / s) if s else 0.0


def evaluate(warped, seg, ref, rubric):
    """ref: dict of template arrays. Returns the metric dictionary."""
    thr = rubric.get("prior_threshold", 0.5)
    brain = ref["brain_mask"]
    vox_cm3 = float(np.prod(rubric["grid"]["zooms_mm"]) / 1000.0)
    m = {}

    for name, code in rubric.get("tissue_labels", TISSUES).items():
        agent = seg == code
        target = ref[f"prior_{name}"] >= thr
        m[f"dice_{name.lower()}"] = dice(agent, target)
        m[f"vol_{name.lower()}_cm3"] = float(agent.sum() * vox_cm3)

    agent_brain = seg > 0
    m["brain_dice"] = dice(agent_brain, brain)
    m["brain_volume_cm3"] = float(agent_brain.sum() * vox_cm3)
    ref_brain_cm3 = float(brain.sum() * vox_cm3)
    m["abs_brain_volume_err_pct"] = 100 * abs(m["brain_volume_cm3"] - ref_brain_cm3) / ref_brain_cm3

    # image similarity inside the template brain, so a retained skull cannot dominate it
    a = warped[brain].astype(np.float64)
    b = ref["T1w"][brain].astype(np.float64)
    if a.std() > 0 and b.std() > 0:
        m["corr_in_brain"] = float(np.corrcoef(a, b)[0, 1])
    else:
        m["corr_in_brain"] = 0.0

    # how far the propagated brain sits from where it belongs; catches a warp that is
    # globally displaced while still overlapping
    if agent_brain.any():
        com_a = np.array(ndi.center_of_mass(agent_brain))
        com_b = np.array(ndi.center_of_mass(brain))
        zooms = np.asarray(rubric["grid"]["zooms_mm"], float)
        m["com_offset_mm"] = float(np.linalg.norm((com_a - com_b) * zooms))
    else:
        m["com_offset_mm"] = np.inf
    return m


def validity_gates(warped, seg, notes_w, notes_s, rubric, m, nonfinite_w, brain):
    g = {}
    g["warped_on_template_grid"] = not any(n.startswith("grid_mismatch") for n in notes_w)
    g["dseg_on_template_grid"] = not any(n.startswith("grid_mismatch") for n in notes_s)
    # NaN outside the head is a resampler convention; NaN inside the brain is a broken warp
    g["warped_finite_in_brain"] = not bool((nonfinite_w & brain).any())
    codes = set(rubric.get("tissue_labels", TISSUES).values())
    present = set(np.unique(seg).astype(int).tolist()) - {0}
    g["valid_labels"] = present.issubset(codes) and len(present) >= 2
    g["nonempty"] = bool((seg > 0).any())
    lo, hi = rubric["plausible_brain_volume_cm3"]
    g["brain_volume_plausible"] = bool(lo <= m["brain_volume_cm3"] <= hi)
    g["brain_in_place"] = bool(m["com_offset_mm"] <= rubric["max_com_offset_mm"])
    return g


def subscore(value, env, key, slack):
    """Full marks at the median accepted nonlinear registration, zero credit at `floor`.

    `floor` is the median of the affine-only arms, so the scale reads directly: 0 means the
    submission did no better than a 12-DOF affine, 100 means it matched a typical nonlinear
    registration. Anchoring on the affine rather than on a slack multiple of the accepted spread
    matters here because the accepted tools agree very closely (WM Dice within 0.015 of each
    other) — a slack-based floor would sit inside that spread and make the score brittle.
    """
    lo_better = key in LOWER_BETTER
    full = env["median"]
    zero = env.get("floor")
    if zero is None:                      # no affine arm for this metric: fall back to slack
        worst = env["worst"]
        zero = (worst + slack * abs(worst - full) if lo_better
                else worst - slack * abs(full - worst))
    if lo_better:
        return float(np.clip((zero - value) / max(zero - full, 1e-9), 0, 1))
    return float(np.clip((value - zero) / max(full - zero, 1e-9), 0, 1))


def score(warped_path, dseg_path, pack_dir):
    pack = Path(pack_dir)
    rubric = json.load(open(pack / "rubric.json"))
    refdir = pack / "reference"
    need = ["template_T1w.nii.gz", "template_brain_mask.nii.gz", "template_probseg_CSF.nii.gz",
            "template_probseg_GM.nii.gz", "template_probseg_WM.nii.gz"]
    missing = [n for n in need if not (refdir / n).exists()]
    if missing:
        raise SystemExit(f"ERROR: missing reference file(s) in {refdir}: {missing}. "
                         "Fetch them from OSF (see reference/README.md).")

    tpl_img = nib.as_closest_canonical(nib.load(str(refdir / "template_T1w.nii.gz")))
    ref = {"T1w": np.asanyarray(tpl_img.dataobj).astype(np.float64),
           "brain_mask": np.asanyarray(nib.as_closest_canonical(
               nib.load(str(refdir / "template_brain_mask.nii.gz"))).dataobj) > 0.5}
    for t in rubric.get("tissue_labels", TISSUES):
        ref[f"prior_{t}"] = np.asanyarray(nib.as_closest_canonical(
            nib.load(str(refdir / f"template_probseg_{t}.nii.gz"))).dataobj).astype(np.float64)

    warped, notes_w, nonfinite_w = load_on_grid(warped_path, tpl_img, label=False)
    seg, notes_s, _ = load_on_grid(dseg_path, tpl_img, label=True)
    seg = np.rint(seg).astype(int)

    labels = rubric.get("tissue_labels", TISSUES)
    m = evaluate(warped, seg, ref, rubric)
    gates = validity_gates(warped, seg, notes_w, notes_s, rubric, m, nonfinite_w, ref["brain_mask"])
    failures = [k for k, ok in gates.items() if not ok]

    weights = rubric["weights"]
    subs = {k: subscore(m[k], rubric["envelope"][k], k, rubric["slack"]) for k in weights}
    quality = 100 * sum(weights[k] * subs[k] for k in weights)
    within = all((m[k] <= rubric["envelope"][k]["worst"]) if k in LOWER_BETTER
                 else (m[k] >= rubric["envelope"][k]["worst"]) for k in weights)
    vt = rubric["verdict_thresholds"]
    if failures:
        verdict, quality = "invalid", 0.0
    elif within:
        verdict = "indistinguishable"
    elif quality >= vt["acceptable"]:
        verdict = "acceptable"
    elif quality >= vt["marginal"]:
        verdict = "marginal"
    else:
        verdict = "unacceptable"

    # Diagnostic, never scored. The task says to warp the SUPPLIED segmentation, which keeps
    # 1=GM 2=WM 3=CSF. An agent that instead re-segments with, say, FSL FAST gets the same label
    # set in a different order and scores badly for a reason that looks like bad registration.
    # Naming it turns a confusing zero into an actionable one.
    best_perm, best_mean = None, sum(m[f"dice_{t.lower()}"] for t in labels) / len(labels)
    import itertools as _it
    codes = [labels[t] for t in labels]
    for perm in _it.permutations(codes):
        if list(perm) == codes:
            continue
        alt = {t: perm[i] for i, t in enumerate(labels)}
        mean = sum(dice(seg == alt[t], ref[f"prior_{t}"] >= rubric.get("prior_threshold", 0.5))
                   for t in labels) / len(labels)
        if mean > best_mean:
            best_mean, best_perm = mean, alt
    result_extra = {}
    if best_perm is not None:
        result_extra["suspected_label_permutation"] = {
            "mapping": best_perm, "mean_tissue_dice_if_applied": round(best_mean, 4)}

    return {"verdict": verdict, "quality": round(quality, 2), "gate_failures": failures,
            **result_extra,
            "load_notes": notes_w + notes_s,
            "subscores": {k: round(v, 3) for k, v in subs.items()},
            "metrics": {k: (round(float(v), 4) if np.isfinite(v) else None) for k, v in m.items()}}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Grade a T1w-to-MNI registration.")
    ap.add_argument("--warped", required=True, help="agent T1w resampled into MNI (NIfTI)")
    ap.add_argument("--dseg", required=True,
                    help="agent tissue segmentation carried through the same transform (NIfTI)")
    ap.add_argument("--pack", required=True)
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    r = score(a.warped, a.dseg, a.pack)
    print(json.dumps(r, indent=2))
    if a.json:
        json.dump(r, open(a.json, "w"), indent=2)
    return 0 if not r["gate_failures"] else 1


if __name__ == "__main__":
    sys.exit(main())
