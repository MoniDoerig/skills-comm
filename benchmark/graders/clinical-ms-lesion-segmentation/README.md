# Grader: `clinical-ms-lesion-segmentation`

Grades an **MS white-matter lesion segmentation** against the **expert multi-rater consensus mask**
of `patient01` of the open_ms_data cross-sectional dataset (Ljubljana MS database, CC-BY).

## Why an expert mask, not a consensus of tools

The brain-extraction and tissue graders score against a *tool consensus* — valid because
skull-strippers largely agree. **Lesion segmentation is different:** automated lesion tools disagree
wildly (published Dice on this very cohort spans 0.50–0.74 across methods), so a tool consensus
would be untrustworthy. Here three expert raters segmented the patient independently and the
dataset ships their **consensus**, which IS the ground truth.

Because the individual rater masks are not public and one subject gives no leave-one-out envelope,
the thresholds are **fixed from published results on this same cohort and reference standard** —
see `PROVENANCE.md`.

## Scorer (ships in this pack)

```bash
# fetch the reference (see reference/README.md), then:
python3 score_lesion_seg.py --pred agent_lesion.nii.gz --pack . [--json result.json]
```

The submission is a **binary lesion mask in the FLAIR space of the co-registered resampled images**
(154 × 240 × 240, 1 mm isotropic).

## Metrics

Dice alone is misleading for MS: the burden is multifocal (408 foci here, median 0.011 cm³), and a
tool can capture the large periventricular confluences while missing most lesion *instances*. So
quality combines three:

- **Dice** (weight 0.4) — overlap; full marks at 0.74, zero credit at 0.53.
- **lesion-wise detection F1** (0.4) — precision/recall over lesion instances (connected
  components, ≥ 10 % overlap counts as detected, components < 3 voxels not counted on either side).
  Full 0.70, zero credit at 0.33.
- **absolute volume error %** (0.2) — full ≤ 15 %, zero credit at 50 %.

Verdict: `indistinguishable` when all three hit full marks; else `acceptable`/`marginal`/
`unacceptable` by weighted quality; `invalid` on a gate failure (`binary`, `native_grid`,
`nonempty`, `volume_plausible` at 0.5–150 cm³).

`copy_suspect_dice` additionally reports (never scores) a submission that reproduces the reference
too exactly: the upstream dataset ships `consensus_gt.nii.gz` in the same folder as the images, so a
Dice ≥ 0.995 means the reference was copied rather than segmented.

## Validation

Degrading the expert mask ranks monotonically, and the two catastrophic modes are gated out:

| perturbation | verdict | quality | Dice | lesion F1 |
|---|---|---|---|---|
| self | indistinguishable | 100.0 | 1.000 | 1.000 |
| largest quarter of foci only | acceptable | 82.4 | 0.946 | 0.537 |
| dilate 1 vox | marginal | 56.2 | 0.615 | 1.000 |
| dilate 2 vox | marginal | 40.0 | 0.410 | 1.000 |
| shift 3 mm | unacceptable | 28.3 | 0.276 | 0.407 |
| erode 1 vox | unacceptable | 6.3 | 0.364 | 0.388 |
| erode 2 vox | unacceptable | 0.0 | 0.060 | 0.007 |
| whole brain mask | **invalid** | 0.0 | 0.048 | 0.998 |
| empty | **invalid** | 0.0 | 0.000 | 0.000 |

Two rows are worth reading closely. *Whole brain mask* shows why lesion-wise F1 can never be a gate
on its own — one huge component overlaps every reference lesion, so F1 ≈ 1.0 while Dice is 0.05; the
volume gate is what rejects it. *Largest quarter of foci only* is the grader's known tolerance: a
submission that traces the big confluent lesions perfectly but misses three-quarters of the lesion
instances still reaches `acceptable`, held down from `indistinguishable` by the F1 term alone.

Erosion is harsher than dilation here because most foci are a few voxels across — an intrinsic
property of multifocal MS at 1 mm, not a scoring artefact.

## Layout

```
clinical-ms-lesion-segmentation/
├── rubric.json          # fixed metric thresholds, weights, verdict thresholds, grid
├── score_lesion_seg.py  # the lesion scorer (shared with the stroke and WMH packs)
├── reference/           # expert consensus mask — fetched from OSF
│   ├── README.md
│   └── .gitignore
├── README.md
└── PROVENANCE.md
```

Reference on OSF: project zjqey, `ground_truth/clinical_gt/clinical-ms-lesion-segmentation/`.
