# Provenance — how this grader pack was calibrated

Frozen output of a one-time calibration on **CEREBRUM-7T `ds003642`, `sub-025` `ses-003`** (7T
MP2RAGE, 0.63 mm isotropic, native T1w space) — the same subject as `structural-brain-extraction-7t`,
with an explicit **"remove the dura"** prompt and an added over-inclusion gate. Not re-derived at
grade time.

## What this pack adds over `-7t`

The consensus reference (`consensus_mask.nii.gz`, `consensus_zones.nii.gz`) and every consensus-side
number in `rubric.json` are identical to the `-7t` pack — the brain-keeping requirement is the same.
This pack adds:

- **`reference/dura_envelope.nii.gz`** — the dura-out pial envelope.
- **`dura_max_cm3` = 30.0** — the one-sided over-inclusion cap.
- **`no_dura_inclusion`** in the gate list.

## The dura envelope

A "no dura" requirement cannot be graded from a tool consensus: skull-strippers disagree on the dura,
so a consensus blurs it into the (unscored) margin. It needs a **dura-out reference**. CEREBRUM-7T
ships four whole-brain tissue segmentations (CEREBRUM7T, FreeSurfer v6/v7, nighres), all dura-out by
construction.

Envelope construction:

1. **Union** of the four segmentations. Union (not majority) is used because the cerebrum-focused
   segmentations under-cover the cerebellum + brainstem; FreeSurfer supplies them, and the union
   keeps them. (Majority-of-4 and FreeSurfer-alone both cut across the cerebellum, which would
   wrongly flag the inferior brain of a good mask as "dura".)
2. **Sulci-fill** by a 5-voxel (3.1 mm) ball closing + hole-fill + largest component, so the
   boundary is the outer **pial** surface. This makes the gate penalise dura (outside the pial
   envelope), **not** sulcal CSF (inside it). Volume ≈ 1202 cm³.

The 3.1 mm radius was chosen from a sweep: 1.9 mm leaves some sulci open (risking false dura flags),
4.4 mm starts bulging toward the dura. 3.1 mm bridges the sulci while hugging the pial surface.

## The cap

`dura_over_env_cm3 = volume(mask AND NOT envelope)` measured on the subject's tools:

| tool       | over-envelope | reading                       |
|------------|---------------|-------------------------------|
| AFNI       | 7 cm³         | dura-out                      |
| HD-BET     | 18 cm³        | small inferior brainstem nub  |
| SynthStrip | 118 cm³       | thick CSF + dura rim          |

**`dura_max_cm3` = 30 cm³ (fixed)** passes the dura-out tools (AFNI, HD-BET) and fails the
rim-retaining tool (SynthStrip) with wide margin. It is a *fixed* cap, not LOTO-calibrated: with two
dura-out reference tools a leave-one-out estimate would be too noisy, and a competent no-dura mask
retains ~0 dura by construction.

## Caveats

- **HD-BET's 18 cm³ is mostly an inferior brainstem/cord nub, not dura.** The cap tolerates it. A
  stricter reading of "no dura" would tighten the cap, at the risk of failing an otherwise good mask.
- **The envelope leans on the shipped segmentations.** It is a curated dura-out reference, not a
  hand-drawn gold standard; a fully manual dura label would be more rigorous.
