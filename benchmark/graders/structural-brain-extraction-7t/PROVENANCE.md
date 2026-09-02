# Provenance — how this grader pack was calibrated

Frozen output of a one-time calibration on the benchmark subject **CEREBRUM-7T `ds003642`,
`sub-025` `ses-003`** (7T MP2RAGE, 0.63 mm isotropic, native T1w space). Not re-derived at grade time.

## Subject and inputs

CEREBRUM-7T provides MP2RAGE INV1 / INV2 / UNI (BIDS `T1w`) at 0.63 mm on a 7T scanner. The graded
input is the **UNI** image. Its background is salt-and-pepper noise (≈ 80 % of background voxels are
"bright"); the **INV2** magnitude is clean outside the head and is used only to build the reference's
cleaned image.

## Cleaned UNI (reference construction only)

To run the tool panel coherently, the UNI background is zeroed with an INV2-derived head mask
(threshold → largest component → close → fill → light dilation, keeping skull/scalp). This cleaned
image is used **only to build the reference**; submissions are graded on whatever they produce from
the raw dataset, and the robust tools do not require the cleaning (see below).

## Panel curation

Four tools were run on the cleaned UNI (FSL BET -R, HD-BET, AFNI `3dSkullStrip`, SynthStrip; ANTs
omitted — adult-template registration is a poor, slow fit at 7T). Curated by the coherence check:

- **Kept (reference): HD-BET, AFNI, SynthStrip** — mutually coherent (pairwise Dice 0.87–0.93).
- **Dropped: FSL BET -R** — catastrophic outlier (546 cm³ ≈ half a brain, mean pairwise Dice 0.64).
  Intensity-based extraction cannot handle the 7T MP2RAGE contrast + bias. BET remains a scored
  **candidate** (comes out `invalid`), which validates the grader.

## Difficulty is tool choice, not preprocessing

Scored on the raw (uncleaned) UNI against this pack:

| tool (raw UNI)     | verdict             | note                                   |
|--------------------|---------------------|----------------------------------------|
| naive FSL `bet`    | **invalid** (557 cm³) | under-extracts; fails volume + core gates |
| SynthStrip         | indistinguishable   | robust to the noise + 7T contrast      |
| HD-BET             | indistinguishable   | robust to the noise + 7T contrast      |

`bet` fails on the cleaned image too (~546 cm³), so the failure is intrinsic to the tool at 7T, not
a missed denoising step.

## Calibration steps

1. **Geometry harmonisation** onto the reference grid (GRID_TOOL = HD-BET); AFNI's header-only
   deoblique is read on the native grid (the grader carries `grid.raw_affine` to detect the same
   case in a submission).
2. **STAPLE consensus** of the three reference tools → binary consensus (`consensus_mask.nii.gz`,
   1164 cm³; core 986 / margin 334).
3. **Zones** from the agreement fraction → `consensus_zones.nii.gz` (0 = background, 1 = margin, 2 = core).
4. **τ** = 95th percentile of pairwise surface disagreement (≈ 13.4 mm — wide, driven by SynthStrip's
   thick 7T CSF rim). The task's discriminating power is in the **validity gates**, not the envelope.
5. **Envelope** by leave-one-tool-out → per-metric median (full marks) / worst (pass line).
6. **Gate caps:** `focal_max_cm3` (localised core loss) and `focal_bg_max_cm3` = 40 cm³ (fixed).

## Reference data

The `reference/` NIfTIs are **not** in git — they live on the Hugging Face Hub (`neurodeskorg/skills-comm-ground-truth`,
`structural_gt/structural-brain-extraction-7t/`). Fetch them before grading; see
`reference/README.md`. Everything else the grader needs is in `rubric.json`.

## Caveats

- **τ is wide.** The quality score is permissive by design here; the gates do the discrimination.
