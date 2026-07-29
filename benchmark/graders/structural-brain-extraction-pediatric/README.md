# Grader: `structural-brain-extraction-pediatric`

A **consensus-calibrated grader** for the pediatric skull-strip task (ds000228 `sub-pixar017`, ~3.6 yo).
Third subject on the **age axis**, companion to `structural-brain-extraction` (healthy adult) and
`structural-brain-extraction-motion` (motion).

Same design: score a submission against a STAPLE consensus of accepted tools split into core (must keep) /
margin (free, not scored) / background (must exclude), all thresholds calibrated from tool disagreement.
See [`PROVENANCE.md`](PROVENANCE.md).

## Shared scorer (no duplication)

This pack ships only the calibration (`rubric.json`) + the reference pointer — **not** its own scorer.
Grade with the shared scorer from the sibling pack, pointing `--pack` here:

```bash
# fetch the reference (see reference/README.md), then:
python3 ../structural-brain-extraction/score_brain_mask.py \
    --mask agent_mask.nii.gz --pack . [--stripped agent_brain.nii.gz] [--json result.json]
```

> Coupling note: the scorer lives in `../structural-brain-extraction/`. If that task is ever removed,
> move `score_brain_mask.py` to a shared location and update the `invoke` path in each task entry.

## What's specific to pediatric

- **Reference panel = HD_BET + AFNI + SynthStrip + FSL BET -R** — all four were coherent on this child brain
  (pairwise Dice ~0.96, no outlier). **ANTs was excluded**: the adult OASIS template does not fit a 3.6-yo brain.
- **τ ≈ 4.5 mm**, margin 15%; core 1028 cm³. Clean full-FOV subject (an earlier candidate, sub-pixar009, was
  rejected for a field-of-view truncation cutting through the brain).
- SynthStrip is the loosest member (it keeps a thin outer CSF rim — 95% of its surplus is CSF, not dura), so it
  scores `acceptable` rather than `indistinguishable`. Kept for consistency with the healthy panel and for
  algorithmic diversity; the margin absorbs the CSF-rim convention.
- Gates include `no_focal_bg_inclusion` (cap 40 cm³) and `no_focal_core_loss`.

## Layout

```
structural-brain-extraction-pediatric/
├── rubric.json          # frozen calibration: τ, envelope, weights, gate caps
├── reference/           # consensus NIfTIs — FETCHED FROM OSF, not in git
│   ├── README.md        #   OSF location + fetch command
│   └── .gitignore
├── README.md
└── PROVENANCE.md
```

Reference on OSF: project zjqey, `ground_truth/structural_gt/structural-brain-extraction-pediatric/`.
