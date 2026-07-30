# Grader: `structural-brain-extraction-7t-nodura`

A **consensus-calibrated grader with an added dura gate** for the *same* 7T MP2RAGE subject as
`structural-brain-extraction-7t` (CEREBRUM-7T `ds003642`, `sub-025`), but for an **explicit
"remove the dura" prompt**. It tests **instruction-following**: does the submission not only extract
the brain but also strip the dura the prompt asked for?

## Why an explicit no-dura prompt

Skull-strippers disagree on how much of the outer CSF/dura rim to keep, and that is normally an
unstated convention — penalising it would be unfair. Putting **"remove the dura" in the prompt**
turns it into a *stated requirement*: a mask that retains a dura rim is now objectively failing the
task, not picking a defensible convention.

## How it grades

The submission is scored by the **shared scorer**, pointed at this pack:

```bash
# fetch the reference (see reference/README.md), then:
python3 ../structural-brain-extraction/score_brain_mask.py \
    --mask agent_mask.nii.gz --pack . [--stripped agent_brain.nii.gz] [--json result.json]
```

Grading composes two things:

1. **A valid brain extraction** — the same core/margin/background consensus as the `-7t` task
   (the brain, incl. cerebellum + brainstem, must be kept).
2. **The `no_dura_inclusion` gate** — the submission must not extend past the **dura-out pial
   envelope** into the dura/skull. `dura_over_env_cm3 = volume(mask AND NOT envelope)`; the gate
   fails (→ `invalid`) when it exceeds **`dura_max_cm3` = 30 cm³** (fixed). The gate is one-sided:
   keeping *less* than the envelope is not penalised here (the core/focal gates already guard
   against cutting brain).

The gate activates only because this pack ships `reference/dura_envelope.nii.gz`; the shared scorer
skips it for every other pack.

## The envelope (dura-out reference)

Built from the **union of the four whole-brain tissue segmentations** shipped with CEREBRUM-7T
(CEREBRUM7T, FreeSurfer v6/v7, nighres) — all dura-out by construction. The union covers the
cerebellum + brainstem (which the cerebrum-focused segmentations alone miss); the sulci are then
**filled** by a 5-voxel (3.1 mm) morphological closing + hole-fill so the boundary is the outer
**pial** surface. This is deliberate: the envelope penalises *dura*, not *sulcal CSF*. Volume ≈ 1202 cm³.

## Same output, different verdict

The point of the task, scored on this subject's tools:

| tool       | dura beyond envelope | `-7t` (standard) | `-7t-nodura` (this pack) |
|------------|----------------------|------------------|--------------------------|
| AFNI       | 7 cm³                | indistinguishable | indistinguishable        |
| HD-BET     | 18 cm³               | indistinguishable | indistinguishable        |
| SynthStrip | **118 cm³**          | indistinguishable | **invalid** (`no_dura_inclusion`) |

SynthStrip's identical mask passes the standard task and fails the no-dura task — the
instruction-following signal.

## Layout

```
structural-brain-extraction-7t-nodura/
├── rubric.json          # -7t calibration + dura_max_cm3 + the no_dura_inclusion gate
├── reference/           # consensus + dura_envelope NIfTIs — FETCHED FROM OSF, not in git
│   ├── README.md
│   └── .gitignore
├── README.md
└── PROVENANCE.md
```

Reference on OSF: project zjqey, `ground_truth/structural_gt/structural-brain-extraction-7t-nodura/`.
The pack is frozen once; scoring never re-calibrates.
