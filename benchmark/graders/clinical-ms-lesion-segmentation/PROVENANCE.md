# Provenance — how this grader pack was built

Frozen reference for **open_ms_data cross-sectional `patient01`** (Ljubljana MS database, 3 T
FLAIR + T1w + T2w, co-registered and resampled to 1 mm isotropic, 154 × 240 × 240). Multiple
sclerosis white-matter lesions, native FLAIR space of the supplied images.

## Ground truth

`lesion_mask.nii.gz` is the dataset's **multi-rater consensus segmentation**: three expert raters
segmented each patient independently with a semi-automated contouring tool, and the released mask is
their consensus [1]. This is a genuine gold standard, not a tool consensus — automated MS lesion
tools span Dice 0.50–0.74 on this cohort [2], far too wide to average into a reference.

Volume **31.42 cm³**, **408 connected foci** (median 0.011 cm³, largest 4.93 cm³) — a high, strongly
multifocal lesion load.

## Geometry harmonisation

Upstream, `consensus_gt.nii.gz` carries a header translated by up to **0.4 mm** from `FLAIR.nii.gz`,
`T1W.nii.gz` and `brainmask.nii.gz`, which are mutually identical. The offset is sub-voxel and
constant, the shapes are identical, and the mask overlays the FLAIR hyperintensities exactly in
index space (see `qc_00_lesion.png`) — a bookkeeping slip in the upstream resampling, not a real
transform. The pack therefore takes the **voxel data of the published consensus mask on the header
of the FLAIR the task hands out**, so a submission left in the input's own space passes the
`native_grid` gate. Without this step every submission would fail that gate.

## Thresholds are fixed from published results on this same cohort

The individual rater masks are not public, so no inter-rater envelope can be recomputed (unlike the
WMH pack, where observers O3/O4 ship with the data), and a single subject gives no leave-one-out
envelope. The anchors instead come from the LST-AI evaluation table for **`msljub`** [2] — the same
30 patients and the same consensus reference standard graded here:

| method | Dice on msljub | lesion-wise F1 | role |
|---|---|---|---|
| **LST-AI** | 0.74 ± 0.10 | 0.70 ± 0.10 | best published on this dataset → **full marks** |
| SAMSEG | 0.62 ± 0.18 | 0.47 ± 0.17 | mid-band |
| nnU-Net | 0.58 ± 0.17 | 0.54 ± 0.18 | mid-band |
| **LST-LGA** | 0.53 ± 0.21 | 0.33 ± 0.19 | weakest legitimate tool → **zero-credit line** |
| LST-LPA | 0.50 ± 0.21 | 0.28 ± 0.16 | below the line |

| metric | full marks | zero credit | basis |
|---|---|---|---|
| Dice | 0.74 | 0.53 | LST-AI / LST-LGA on this cohort |
| lesion-wise F1 | 0.70 | 0.33 | LST-AI / LST-LGA on this cohort |
| abs. volume error | 15 % | 50 % | shared lesion-pack convention, **not** a published value |

Weights: Dice 0.40, lesion-wise F1 0.40, volume error 0.20 — F1 at parity with Dice because MS
burden is multifocal, so detection, not only boundary overlap, is the clinical quantity (the WMH
pack weights it the same way for the same reason).

**Those anchors transfer only because the lesion-counting convention matches.** [2] counts a
reference lesion as detected at **≥ 10 % overlap** (the pack's `overlap_frac_for_match`) and applies
a **3 mm³ minimum lesion size** (`min_lesion_voxels = 3`). Without the minimum, the F1 anchors would
be systematically unreachable here: 130 of the 408 foci are 1–2 voxels, no tool detects them, and
they hold 0.5 % of the lesion volume. With it, 278 foci count as lesion instances. Dice is computed
on the full masks.

## Validation — perturbing the expert mask

| perturbation | verdict | quality | Dice | lesion F1 | volume |
|---|---|---|---|---|---|
| self | indistinguishable | 100.0 | 1.000 | 1.000 | 31.4 cm³ |
| largest quarter of foci only | acceptable | 82.4 | 0.946 | 0.537 | 28.2 cm³ |
| dilate 1 vox | marginal | 56.2 | 0.615 | 1.000 | 70.7 cm³ |
| dilate 2 vox | marginal | 40.0 | 0.410 | 1.000 | 121.9 cm³ |
| shift 3 mm | unacceptable | 28.3 | 0.276 | 0.407 | 31.4 cm³ |
| erode 1 vox | unacceptable | 6.3 | 0.364 | 0.388 | 7.0 cm³ |
| erode 2 vox | unacceptable | 0.0 | 0.060 | 0.007 | 1.0 cm³ |
| whole brain mask | **invalid** (`volume_plausible`) | 0.0 | 0.048 | 0.998 | 1288.4 cm³ |
| empty | **invalid** (`nonempty`) | 0.0 | 0.000 | 0.000 | 0 cm³ |

The *whole brain mask* row is why lesion-wise F1 can never gate on its own: one huge component
overlaps every reference lesion, so F1 ≈ 1.0 while Dice is 0.05 — the volume gate is what rejects
it. The *largest quarter of foci only* row is the pack's known tolerance: an artificial submission
that traces the big confluent lesions with perfect boundaries but misses three-quarters of the
lesion instances still reaches `acceptable`, held down only by the F1 term. Erosion bites harder
than dilation because most foci are a few voxels across — intrinsic to multifocal MS at 1 mm.

## Difficulty screen — the tool panel

Three tools were run on the task's own inputs and scored through this pack (`qc_02_panel.png`).
Outputs were nearest-neighbour harmonised onto the reference grid before scoring, so a tool's
geometry conventions do not masquerade as segmentation error; none of the three needed it here.

| tool | verdict | quality | Dice | lesion F1 | volume |
|---|---|---|---|---|---|
| **LST-AI** (`lstai/1.2.0`, MS-specific ensemble) | acceptable | 91.3 | 0.719 | 0.747 | 24.1 cm³ |
| SAMSEG (`freesurfer/8.0.0`, `--lesion`) | unacceptable | 0.0 | 0.493 | 0.199 | 13.8 cm³ |
| FLAIR mean + 2 SD inside the brain mask | unacceptable | 0.0 | 0.149 | 0.071 | 3.5 cm³ |

**This is the task's discriminating property: only the MS-specific tool clears the bar.** With the
reporting layer's rule (pass = valid and verdict ≥ acceptable) LST-AI passes and the other two fail,
while all three produce plausible-volume binary masks — so the task separates on tool choice, not on
whether the agent managed to write a NIfTI.

LST-AI's Dice 0.719 / F1 0.747 on this subject sits within a fraction of a standard deviation of its
published means on this cohort (0.74 ± 0.10 / 0.70 ± 0.10). **patient01 is a typical subject for the
cohort the thresholds came from** — the check that makes fixed thresholds defensible on n = 1.

Two honest caveats about the panel. SAMSEG's 0.493 is below its published cohort mean of 0.62,
though inside one standard deviation; this run is one plausible configuration (FLAIR + T1,
`--lesion-mask-pattern 1 0`, FreeSurfer 8.0.0, default lesion threshold), not a tuned reproduction
of the published setup, and the rubric's anchors come from the published table rather than from this
run. And the panel is a difficulty screen, not a calibration input: no threshold in `rubric.json`
was derived from it.

## Reference-leak exposure

The upstream repository stores `consensus_gt.nii.gz` **in the same directory as the images**, in all
three variants (`raw/`, `coregistered/`, `coregistered_resampled/`). The task prompt therefore
fetches the three input files individually by URL rather than cloning the repository, and the pack
sets `copy_suspect_dice = 0.995`: a submission that reproduces the reference too exactly is reported
as `suspected_reference_copy` in the scorer output. That flag never changes the verdict — the
harness decides what to do with a flagged run.

## Reference data (on OSF)

`reference/lesion_mask.nii.gz` is **not** in git — it lives on OSF (zjqey,
`ground_truth/clinical_gt/clinical-ms-lesion-segmentation/`). Fetch it before grading; see
`reference/README.md`. Everything else the grader needs is in `rubric.json`. The Ljubljana database
is CC-BY, so the mask is redistributable with attribution.

## References

1. Lesjak Ž, Galimzianova A, Koren A, Lukin M, Pernuš F, Likar B, Špiclin Ž. A Novel Public MR Image
   Dataset of Multiple Sclerosis Patients With Lesion Segmentations Based on Multi-rater Consensus.
   *Neuroinformatics* 16:51–63, 2018. doi:10.1007/s12021-017-9348-7
2. Wiltgen T, McGinnis J, Schlaeger S, et al. LST-AI: A deep learning ensemble for accurate MS
   lesion segmentation. *NeuroImage: Clinical* 42:103611, 2024. doi:10.1016/j.nicl.2024.103611
