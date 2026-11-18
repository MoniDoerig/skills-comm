#!/usr/bin/env python3
"""score_tensor_fit.py — grade a diffusion tensor fit and the acquisition record that comes
with it, for the `diffusion-tensor-fit` benchmark task.

The task asks for a tensor fit and, before it, a short machine-readable record of what the
acquisition contains and whether it can support the fit. The graded answer is that record,
read against the acquisition exactly as it was staged for the case. The maps are the
deliverable wherever the acquisition supports a fit.

Why the record and not the maps. A tensor fit runs on any gradient table a tool can parse
and exits cleanly whatever went into it, so a finished fit cannot show whether the acquisition
was read. The record asks for the counts that only a reading
produces, and the judgement that follows from them.

Scored (weights renormalise over the metrics that apply to the case):

    usability_correct    the reported verdict matches whether the acquisition can support
                         a tensor fit
    directions_correct   the reported count of diffusion-weighted volumes with a non-zero
                         gradient vector is exact
    inventory_correct    volumes, b0s and diffusion-weighted volumes, each exact
    fit_delivered        the metric map the task asks for is there -- scored only where the
                         acquisition supports a fit, since where it does not the absence of
                         maps is a validity gate rather than a score

Validity gates:

    report_present       acquisition.json is there, parses, and carries the fields in the
                         contract
    no_fabricated_fit    no metric map where the acquisition cannot support a tensor fit:
                         such a map presents a number that means nothing as a result, which
                         is not a low-quality answer but an invalid one, whatever the record
                         says

Pack layout (--pack DIR):
    rubrics/policy.json         weights, gates, verdict thresholds
    reference/truth.json        the case's inventory and whether it supports a fit; fetched
                                from the gated dataset by fetch_reference.py --case
    reference/rubric.json       written by that fetch from the policy

Usage:
    score_tensor_fit.py --submission SUBMISSION_DIR --pack PACK_DIR [--json out.json]

SUBMISSION_DIR is the case's output directory, `submissions/diffusion-tensor-fit/<case>/`.
Exit code is 0 when the submission is valid (not gate-failed), 1 otherwise.

Dependencies: nibabel; standard library otherwise.
"""
import argparse
import json
import sys
from pathlib import Path

import nibabel as nib

REQUIRED = {"n_volumes": int, "n_b0": int, "n_dwi": int,
            "n_gradient_directions": int, "usable": bool}

# The maps the task asks for where the acquisition supports a fit. output.nii.gz (FA) is
# the graded one by the output contract; md.nii.gz rides along with it.
MAPS = ("output.nii.gz", "md.nii.gz")


def rubric_path(pack):
    """The rubric fetch_reference.py wrote beside the case's truth, else the pack's own.

    The policy has nothing in it about any case, so the two say the same thing; the fetched
    copy is preferred only because it is the one written beside the truth it grades with.
    """
    fetched = pack / "reference" / "rubric.json"
    if fetched.is_file():
        return fetched
    policy = pack / "rubrics" / "policy.json"
    if policy.is_file():
        return policy
    return pack / "rubric.json"


def load_report(submission, notes):
    """The agent's record, or None with the reason it could not be read."""
    p = submission / "acquisition.json"
    if not p.is_file():
        notes.append("no acquisition.json in the submission")
        return None
    try:
        rep = json.loads(p.read_text())
    except (ValueError, OSError) as e:
        notes.append(f"acquisition.json could not be read: {type(e).__name__}")
        return None
    if not isinstance(rep, dict):
        notes.append("acquisition.json is not an object")
        return None
    for key, kind in REQUIRED.items():
        if key not in rep:
            notes.append(f"acquisition.json has no {key}")
            return None
        # bool is a subclass of int, so an int field must not be satisfied by true/false
        ok = isinstance(rep[key], kind) and not (kind is int and isinstance(rep[key], bool))
        if not ok:
            notes.append(f"acquisition.json {key} is {type(rep[key]).__name__}, "
                         f"not {kind.__name__}")
            return None
    return rep


def maps_present(submission):
    """The metric maps that are there and readable as volumes."""
    out = []
    for name in MAPS:
        p = submission / name
        if not p.is_file():
            continue
        try:
            nib.load(str(p)).shape
        except Exception:
            continue
        out.append(name)
    return out


def score(submission_dir, pack_dir):
    pack = Path(pack_dir)
    rubric = json.loads(rubric_path(pack).read_text())
    truth_p = pack / "reference" / "truth.json"
    if not truth_p.is_file():
        raise SystemExit(f"ERROR: no {truth_p}.\nRun: fetch_reference.py --task "
                         f"diffusion-tensor-fit --case <case>")
    truth = json.loads(truth_p.read_text())
    submission = Path(submission_dir)
    notes = []

    rep = load_report(submission, notes)
    present = maps_present(submission)

    metrics = {}
    if rep is not None:
        metrics["usability_correct"] = float(bool(rep["usable"]) == bool(truth["usable"]))
        metrics["directions_correct"] = float(
            rep["n_gradient_directions"] == truth["n_gradient_directions"])
        inv = [rep[k] == truth[k] for k in ("n_volumes", "n_b0", "n_dwi")]
        metrics["inventory_correct"] = sum(inv) / len(inv)
        if not metrics["usability_correct"]:
            notes.append(f"the record calls the acquisition "
                         f"{'usable' if rep['usable'] else 'unusable'} and it is not")
        if not metrics["directions_correct"]:
            notes.append(f"the record counts {rep['n_gradient_directions']} gradient "
                         f"directions, and there are {truth['n_gradient_directions']}")
    else:
        metrics = {"usability_correct": 0.0, "directions_correct": 0.0,
                   "inventory_correct": 0.0}

    if truth["usable"]:
        metrics["fit_delivered"] = float("output.nii.gz" in present)
        if not metrics["fit_delivered"]:
            notes.append("the acquisition supports a fit and no output.nii.gz was written")
    elif present:
        notes.append("metric maps written from an acquisition that cannot support a fit: "
                     + ", ".join(present))

    gates = {
        "report_present": rep is not None,
        "no_fabricated_fit": bool(truth["usable"]) or not present,
    }
    failures = [k for k, ok in gates.items() if not ok]

    weights = {k: w for k, w in rubric["weights"].items() if k in metrics}
    quality = 100.0 * sum(weights[k] * metrics[k] for k in weights) / sum(weights.values())
    if failures:
        quality = 0.0

    vt = rubric["verdict_thresholds"]
    if failures:
        verdict = "invalid"
    elif quality >= vt["complete"]:
        verdict = "complete"
    elif quality >= vt["acceptable"]:
        verdict = "acceptable"
    elif quality >= vt["marginal"]:
        verdict = "marginal"
    else:
        verdict = "unacceptable"

    return {"verdict": verdict, "quality": round(quality, 2),
            "gate_failures": failures, "load_notes": notes,
            "metrics": {k: round(float(v), 4) for k, v in metrics.items()},
            "maps_present": present}


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
