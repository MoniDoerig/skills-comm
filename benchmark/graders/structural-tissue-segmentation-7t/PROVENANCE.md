# Provenance — how this grader pack was calibrated

Frozen output of a one-time calibration on **CEREBRUM-7T `ds003642`, `sub-025` `ses-003`** (7T
MP2RAGE, 0.63 mm isotropic, native T1w space). Not re-derived at grade time.

## Why consensus, not a single truth

Every tissue/structure segmenter draws slightly different boundaries, especially at the fuzzy
partial-volume interfaces (GM↔WM, GM↔CSF). Grading against one tool's output would bake in that
tool's idiosyncrasies. Instead the reference is a **majority vote of accepted segmentations**, split
into per-class zones — unanimous core (must match) and majority boundary (partial-volume, softly
scored) — and only the calibrated envelope decides pass/fail.

## Panel (pre-computed, no tools run)

CEREBRUM-7T ships four whole-brain segmentations. Curated by the coherence check:

- **Kept: CEREBRUM7T, FreeSurfer v6, FreeSurfer v7** — share a common 7-label scheme (per-class
  Dice 0.75–0.92 between them).
- **Dropped: nighres** — a coherence outlier; its label-3 (WM) Dice vs the others is 0.09, i.e. a
  different label protocol. Kept as a scored candidate; it comes out `invalid`.

## Label legend (confirmed by intensity on the UNI)

`1=GM  2=basal ganglia  3=WM  4=ventricles/CSF  5=cerebellum  6=brainstem` (0 = background). The
integer mapping is not published by CEREBRUM-7T; it was pinned by class volume + median UNI
intensity (WM brightest 2564, basal ganglia 2187, GM 1407, ventricles darkest 691).

## Consensus and calibration

1. **Fuse** the three tools by per-voxel majority vote (≥ 2/3) over the 7 classes →
   `consensus_seg.nii.gz`; `consensus_agreement.nii.gz` records the winning vote count (3 = unanimous
   core, 2 = majority boundary). Three-way ties are 1.4 cm³ total.
2. **Class volumes (cm³):** GM 485, basal ganglia 42, WM 360, ventricles 10, cerebellum 76,
   brainstem 14. Unanimous-core fraction ranges 67 % (GM — fuzziest) to 87 % (WM — tightest).
3. **Per-class τ** = 95th percentile of pairwise surface disagreement among the three tools (mm):
   GM 1.77, basal ganglia 1.77, WM 1.25, ventricles 1.53, **cerebellum 7.56** (widest — the
   cerebellar boundary is genuinely fuzzy at this resolution), brainstem 3.12.
4. **Envelope** by leave-one-tool-out → per-class median (full marks) / worst (pass line). LOTO Dice
   median/worst: GM 0.785/0.760, basal ganglia 0.881/0.880, WM 0.905/0.901, ventricles 0.816/0.805,
   cerebellum 0.855/0.741, brainstem 0.858/0.836.

## Scoring

Per class: Dice, NSD (within τ), core-recall; each mapped through its envelope with `slack` 1.5.
Overall quality = mean of the six class qualities. Gates → `invalid`: `valid_labels`, `native_grid`,
`no_class_collapse` (each class recovers ≥ 50 % of its unanimous core).

## Validation

Scored against the frozen pack: CEREBRUM7T `indistinguishable` (q99.4), FreeSurfer v6 / v7
`indistinguishable` (q100), and the dropped **nighres `invalid`** (WM Dice 0.09 →
`no_class_collapse`) — the outlier is rejected, confirming the grader discriminates.

## Reference data

`reference/consensus_seg.nii.gz` + `consensus_agreement.nii.gz` are on the Hugging Face Hub
(`neurodeskorg/skills-comm-ground-truth`, `structural_gt/structural-tissue-segmentation-7t/`). Fetch them before grading;
see `reference/README.md`. Everything else is in `rubric.json`.

## Caveats

- **Six-structure parcellation, not classic 3-class GM/WM/CSF.** The classes follow the CEREBRUM-7T
  protocol (basal ganglia, cerebellum, brainstem are their own labels; CSF is ventricular). An agent
  must output this exact legend.
- **The panel are DL/atlas segmentations, not a manual gold standard** — a curated consensus, not
  ground truth in the strict sense. Two of three are FreeSurfer versions, so the consensus leans
  FreeSurfer-ward; CEREBRUM7T (7T-specialised) adds independent signal.
