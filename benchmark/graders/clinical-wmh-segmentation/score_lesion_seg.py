#!/usr/bin/env python3
"""score_lesion_seg.py — grade a lesion-segmentation submission against a frozen EXPERT mask.

Unlike the brain-extraction / tissue graders (which score against a tool *consensus*), lesion
segmentation is graded against a single expert manual mask — automated lesion tools disagree too
much to form a trustworthy consensus, so the dataset's expert tracing IS the ground truth. Because
one subject gives no leave-one-out envelope, the pass/fail thresholds are FIXED from the literature
(chronic-stroke inter-rater Dice ~0.7), recorded in rubric.json.

Metrics:
  dice                overlap with the expert mask
  lesion_f1           lesion-WISE detection F1 (connected components; small lesions that tank Dice
                      still register as detected/missed) — precision/recall over lesion instances
  abs_volume_err_pct  |predicted - expert| volume, % of expert

Pack (--pack DIR): rubric.json + reference/lesion_mask.nii.gz (expert mask, native grid).
Usage:  score_lesion_seg.py --pred agent_lesion.nii.gz --pack PACK_DIR [--json out.json]
Exit 0 when valid (verdict != invalid), 1 otherwise. Deps: numpy, scipy, nibabel.
"""
import argparse, json, sys
from pathlib import Path
import numpy as np, nibabel as nib
from scipy import ndimage as ndi

BIN_TOL = 1e-6
STRUCT = ndi.generate_binary_structure(3, 1)


def same_grid(a, b, tol=1e-3):
    return a.shape[:3] == b.shape[:3] and np.allclose(a.affine, b.affine, atol=tol)


def load_mask(path, ref_img):
    raw = nib.load(str(path)); img = nib.as_closest_canonical(raw)
    data = np.nan_to_num(np.asanyarray(img.dataobj).astype(np.float64))
    notes = []
    vals = np.unique(data)
    if vals.size > 2 or not np.isin(vals, [0, 1]).all():
        notes.append("not_binary")
    m = data > BIN_TOL
    if not same_grid(img, ref_img):
        notes.append(f"grid_mismatch{tuple(img.shape[:3])}")
        xfm = np.linalg.inv(img.affine) @ ref_img.affine
        m = ndi.affine_transform(m.astype(np.uint8), xfm[:3, :3], offset=xfm[:3, 3],
                                 output_shape=ref_img.shape[:3], order=0, mode="constant", cval=0) > 0
        notes.append("resampled_nn")
    return m, notes


def lesion_wise_f1(pred, ref, min_overlap):
    """Detection F1 over connected components. A reference lesion counts detected if a predicted
    component overlaps >= min_overlap of it; a predicted component is a false positive if it
    overlaps no reference lesion."""
    rl, nr = ndi.label(ref, STRUCT)
    pl, npd = ndi.label(pred, STRUCT)
    if nr == 0 and npd == 0:
        return 1.0, 1.0, 1.0, 0, 0, 0
    tp = 0
    for i in range(1, nr + 1):
        comp = rl == i
        if (pred & comp).sum() >= min_overlap * comp.sum():
            tp += 1
    fn = nr - tp
    fp = 0
    for j in range(1, npd + 1):
        comp = pl == j
        if (ref & comp).sum() == 0:
            fp += 1
    prec = tp / max(tp + fp, 1)
    rec = tp / max(tp + fn, 1)
    f1 = 2 * prec * rec / max(prec + rec, 1e-9)
    return f1, prec, rec, tp, fp, fn


def surface_metrics(pred, ref, zooms):
    sp = pred & ~ndi.binary_erosion(pred, STRUCT, border_value=1)
    sr = ref & ~ndi.binary_erosion(ref, STRUCT, border_value=1)
    if sp.sum() == 0 or sr.sum() == 0:
        return dict(assd_mm=np.nan, hd95_mm=np.nan)
    d1 = ndi.distance_transform_edt(~sr, sampling=zooms)[sp]
    d2 = ndi.distance_transform_edt(~sp, sampling=zooms)[sr]
    both = np.concatenate([d1, d2])
    return dict(assd_mm=float(both.mean()), hd95_mm=float(np.percentile(both, 95)))


def subscore(value, full, pass_, lower_better=False):
    if not np.isfinite(value):
        return 0.0
    if lower_better:
        return float(np.clip((pass_ - value) / max(pass_ - full, 1e-9), 0, 1))
    return float(np.clip((value - pass_) / max(full - pass_, 1e-9), 0, 1))


def score(pred_path, pack_dir):
    pack = Path(pack_dir); rubric = json.load(open(pack / "rubric.json"))
    ref_p = pack / "reference" / "lesion_mask.nii.gz"
    if not ref_p.exists():
        raise SystemExit(f"ERROR: reference/lesion_mask.nii.gz not in {pack/'reference'}. "
                         "Fetch from OSF (see reference/README.md).")
    rimg = nib.as_closest_canonical(nib.load(str(ref_p)))
    ref = np.asanyarray(rimg.dataobj) > BIN_TOL
    zooms = np.asarray(rimg.header.get_zooms()[:3], float)
    vox_cm3 = float(np.prod(zooms) / 1000.0)

    pred, notes = load_mask(pred_path, rimg)
    th = rubric["metric_thresholds"]
    m = {}
    m["dice"] = 2 * (pred & ref).sum() / max(pred.sum() + ref.sum(), 1)
    f1, prec, rec, tp, fp, fn = lesion_wise_f1(pred, ref, rubric.get("overlap_frac_for_match", 0.1))
    m["lesion_f1"] = f1; m["lesion_precision"] = prec; m["lesion_recall"] = rec
    m["tp"], m["fp"], m["fn"] = tp, fp, fn
    m["pred_vol_cm3"] = float(pred.sum() * vox_cm3); m["ref_vol_cm3"] = float(ref.sum() * vox_cm3)
    m["abs_volume_err_pct"] = 100 * abs(pred.sum() - ref.sum()) / max(ref.sum(), 1)
    m.update(surface_metrics(pred, ref, zooms))

    gates = {}
    gates["binary"] = "not_binary" not in notes
    gates["native_grid"] = not any(n.startswith("grid_mismatch") for n in notes)
    gates["nonempty"] = bool(pred.sum() > 0)
    lo, hi = rubric.get("plausible_vol_cm3", [0.1, 500])
    gates["volume_plausible"] = bool(lo <= m["pred_vol_cm3"] <= hi)
    failures = [k for k, ok in gates.items() if not ok]

    weights = rubric["weights"]
    subs = {
        "dice": subscore(m["dice"], th["dice"]["full"], th["dice"]["pass"]),
        "lesion_f1": subscore(m["lesion_f1"], th["lesion_f1"]["full"], th["lesion_f1"]["pass"]),
        "abs_volume_err_pct": subscore(m["abs_volume_err_pct"], th["abs_volume_err_pct"]["full"],
                                       th["abs_volume_err_pct"]["pass"], lower_better=True),
    }
    quality = 100 * sum(weights[k] * subs[k] for k in weights)
    within = (m["dice"] >= th["dice"]["full"] and m["lesion_f1"] >= th["lesion_f1"]["full"]
              and m["abs_volume_err_pct"] <= th["abs_volume_err_pct"]["full"])
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

    return {"verdict": verdict, "quality": round(quality, 2), "gate_failures": failures,
            "load_notes": notes, "subscores": {k: round(v, 3) for k, v in subs.items()},
            "metrics": {k: round(float(v), 4) for k, v in m.items()}}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Grade a lesion segmentation against the frozen expert mask.")
    ap.add_argument("--pred", required=True, help="agent lesion mask (NIfTI, binary)")
    ap.add_argument("--pack", required=True)
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    r = score(a.pred, a.pack)
    print(json.dumps(r, indent=2))
    if a.json:
        json.dump(r, open(a.json, "w"), indent=2)
    return 0 if not r["gate_failures"] else 1


if __name__ == "__main__":
    sys.exit(main())
