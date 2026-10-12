# Grader: `structural-brain-extraction-motion`

A **consensus-calibrated grader** for the harder, motion-corrupted skull-strip task
(MR-ART `ds004173`, `sub-000103`, `acq-headmotion2` — the worst-motion tier). It is the
companion to `structural-brain-extraction` (the healthy-adult baseline) on the **motion axis**.

Same design: score a submission against a STAPLE consensus of accepted tools split into
core (must keep) / margin (free, not scored) / background (must exclude), with all thresholds
calibrated from the tools' own disagreement. See [`PROVENANCE.md`](PROVENANCE.md).

## Shared scorer (no duplication)

This pack carries **only the calibration** (`rubric.json`) and the reference pointer — it does
**not** ship its own scorer. Grade with the shared scorer from the sibling pack, pointing `--pack`
here:

```bash
# fetch the reference (see reference/README.md), then:
python3 ../structural-brain-extraction/score_brain_mask.py \
    --mask agent_mask.nii.gz --pack . [--stripped agent_brain.nii.gz] [--json result.json]
```

> Coupling note: the scorer currently lives in `../structural-brain-extraction/`. If that task is
> ever removed, move `score_brain_mask.py` to a shared location (e.g. `benchmark/graders/`) and
> update the `invoke` path in both task entries — a one-line change.

## What's different from the baseline

On the motion scan the tools **diverge and partly fail**, so the reference panel is curated:

- **Reference panel = HD_BET + AFNI + SynthStrip.** ANTs and FSL BET were dropped — ANTs is a
  coherence outlier (mean pairwise Dice 0.81 vs 0.90+), and both extended into the neck/spinal
  cord ("too much left at the bottom"), inflating the margin.
- **τ ≈ 5.7 mm** (vs 3.7 on the healthy adult) — the motion boundary is genuinely fuzzier, so a
  wider tolerance is data-justified.
- The gates include **`no_focal_bg_inclusion`** (cap `focal_bg_max_cm3` = 40 cm³, fixed) — it fails
  a mask that retains a large contiguous chunk of non-brain (e.g. neck), the mirror of the
  focal-loss gate. This is what makes an over-inclusive BET-style output fail here.

## Layout

```
structural-brain-extraction-motion/
├── rubric.json          # frozen calibration: τ, envelope, weights, gate caps (incl. focal_bg_max_cm3)
├── reference/           # consensus NIfTIs — fetched from the Hub
│   ├── README.md        #   dataset path + fetch command
│   └── .gitignore
├── README.md
└── PROVENANCE.md
```

Reference: Hugging Face `neurodeskorg/skills-comm-ground-truth`, path `structural_gt/structural-brain-extraction-motion/`.
The pack is frozen once; scoring never re-calibrates.
