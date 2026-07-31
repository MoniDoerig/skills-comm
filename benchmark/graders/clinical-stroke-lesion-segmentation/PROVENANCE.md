# Provenance — how this grader pack was built

Frozen reference for **Aphasia Recovery Cohort (ARC), OpenNeuro `ds004884`, `sub-M2191` `ses-681`**
(chronic left-MCA stroke, native T1w space).

## Ground truth

The reference `lesion_mask.nii.gz` is the dataset's **expert manual lesion tracing** — drawn in T2w
space by trained raters — rigid-registered (FSL FLIRT, 6 DOF, nearest-neighbour) into the native T1w
space so both stroke tasks share one space. Volume 82.8 cm³. This is a genuine gold standard, not a
tool consensus (see the README for why lesion segmentation cannot use a consensus).

## Thresholds are fixed, not calibrated by LOTO

A single subject gives no leave-one-tool-out envelope, and a tool-consensus would be untrustworthy for
lesions. So the pass/fail lines are **fixed from the literature**:

| metric | full marks | pass line | basis |
|---|---|---|---|
| Dice | 0.70 | 0.50 | chronic-stroke inter-rater / state-of-the-art Dice ≈ 0.7 |
| lesion-wise F1 | 1.0 | 0.5 | detect the lesion instance(s) |
| abs. volume error | 15 % | 50 % | gross size plausibility |

Weights: Dice 0.5, lesion-wise F1 0.3, volume error 0.2. A connected component counts as detected when
a prediction overlaps ≥ 10 % of it.

## Validation

Perturbing the expert mask against the pack: self → `indistinguishable` (q100, Dice 1.0); dilated 3
vox → `acceptable` (q80, Dice 0.74, volume +72 %); eroded 4 vox → `unacceptable` (Dice 0.48, F1 0.40);
empty → `invalid` (nonempty gate).

## Reference data (on OSF)

`lesion_mask.nii.gz` is **not** in git — OSF (zjqey,
`ground_truth/clinical_gt/clinical-stroke-lesion-segmentation/`). Fetch before grading; see
`reference/README.md`.

## Caveats

- **n = 1 subject**, one large single lesion. The lesion-wise F1 machinery generalises to
  multi-focal cases, but the thresholds were not tuned on a multi-lesion subject.
- **Registration error** from the T2w→T1w mapping is possible (small; intra-session, rigid, 1 mm).
- **Fixed thresholds** are a literature prior, not this subject's inter-rater spread (ARC ships one
  tracing per subject). A multi-rater subset would let the tolerance be data-derived.
