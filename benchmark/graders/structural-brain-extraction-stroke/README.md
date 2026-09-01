# Grader: `structural-brain-extraction-stroke`

A **consensus-calibrated brain-extraction grader** for a **lesioned (chronic-stroke) brain**
(Aphasia Recovery Cohort, OpenNeuro `ds004884`, `sub-M2191`). Companion to the other
`structural-brain-extraction-*` tasks on the **pathology axis**: does the skull-strip keep the
lesion, or carve it out?

Same design as the baseline: score a submission against a STAPLE consensus of accepted tools split
into core / margin / background, thresholds calibrated by leave-one-tool-out. See
[`PROVENANCE.md`](PROVENANCE.md).

## Shared scorer

No scorer ships here — grade with the shared scorer, pointing `--pack` at this pack:

```bash
# fetch the reference (see reference/README.md), then:
python3 ../structural-brain-extraction/score_brain_mask.py \
    --mask agent_mask.nii.gz --pack . [--stripped agent_brain.nii.gz] [--json result.json]
```

## What's hard here — and the lesion gate

The graded T1w has an 82.8 cm³ chronic infarct: a fluid-filled cavity that is **dark and CSF-like on
T1**. Intensity-based strippers treat it as non-brain and cut it out — **FSL BET retains only 52 % of
the lesion**, while HD-BET (99.6 %), AFNI (93.7 %) and SynthStrip (100 %) keep it.

Because the dataset ships an expert lesion mask, this pack adds a **`lesion_retained` gate**: the brain
mask must contain at least `lesion_retained_min` (0.85) of the expert lesion, else `invalid`. This is
the specific failure the subject exposes, made explicit and lesion-aware (BET also trips the generic
`no_focal_core_loss` gate, but `lesion_retained` names *why*). The gate activates only because this
pack ships `reference/lesion_mask.nii.gz`; the shared scorer skips it for every other pack.

## Reference panel

- **Panel = HD-BET + AFNI + SynthStrip** (the lesion-retaining tools; τ ≈ 5.4 mm).
- **Dropped: FSL BET** — carves out the lesion (52 % retained). Kept as a scored **candidate**; it
  comes out `invalid` (`lesion_retained` + `no_catastrophic_core_loss` + `no_focal_core_loss`),
  which validates the grader.

## Geometry note

The expert lesion mask was drawn in **T2w** space; it was rigid-registered (FSL FLIRT, 6 DOF) into the
native **T1w** space during ground-truth construction, so the whole task lives in one native T1w
space. See PROVENANCE.

## Layout

```
structural-brain-extraction-stroke/
├── rubric.json          # τ, envelope, weights, gate caps, lesion_retained_min, grid.raw_affine
├── reference/           # consensus + lesion NIfTIs — fetched from OSF
│   ├── README.md
│   └── .gitignore
├── README.md
└── PROVENANCE.md
```

Reference on OSF: project zjqey, `ground_truth/structural_gt/structural-brain-extraction-stroke/`.
Companion lesion-segmentation task: `clinical-stroke-lesion-segmentation` (same subject).
