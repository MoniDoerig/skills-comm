# Grader: `clinical-stroke-lesion-segmentation`

Grades a **stroke-lesion segmentation** against an **expert manual mask** (Aphasia Recovery Cohort,
OpenNeuro `ds004884`, `sub-M2191`). Step 2 of the stroke pair; step 1 is
`structural-brain-extraction-stroke` (same subject).

## Why an expert mask, not a consensus

The brain-extraction and tissue graders score against a *tool consensus* — valid because
skull-strippers largely agree. **Lesion segmentation is different:** automated lesion tools disagree
wildly, so a tool-consensus would be untrustworthy. Here the dataset's **expert manual tracing IS the
ground truth**. Because one subject gives no leave-one-out envelope, the pass/fail thresholds are
**fixed from the literature** (chronic-stroke inter-rater Dice ≈ 0.70), recorded in `rubric.json`.

## Scorer (ships in this pack)

```bash
# fetch the reference (see reference/README.md), then:
python3 score_lesion_seg.py --pred agent_lesion.nii.gz --pack . [--json result.json]
```

The submission is a **binary lesion mask in native T1w space**.

## Metrics

Dice alone is misleading for lesions (a small lesion tanks Dice even when correctly found), so quality
combines three:

- **Dice** (weight 0.5) — overlap; full marks at 0.70, pass at 0.50.
- **lesion-wise detection F1** (0.3) — precision/recall over *lesion instances* (connected
  components); a predicted blob overlapping no true lesion is a false positive, a missed lesion a
  false negative. Full 1.0, pass 0.5.
- **absolute volume error %** (0.2) — full ≤ 15 %, pass ≤ 50 %.

Verdict: `indistinguishable` when all three hit full marks; else `acceptable`/`marginal`/
`unacceptable` by weighted quality; `invalid` on a gate failure (`binary`, `native_grid`, `nonempty`,
`volume_plausible`).

## Validation

Perturbing the expert mask: self → `indistinguishable` (q100); dilated 3 vox → `acceptable` (q80,
Dice 0.74); eroded 4 vox → `unacceptable` (Dice 0.48); empty → `invalid`.

## Layout

```
clinical-stroke-lesion-segmentation/
├── rubric.json          # fixed metric thresholds, weights, verdict thresholds, grid
├── score_lesion_seg.py  # the lesion scorer
├── reference/           # expert lesion mask — fetched from the Hub
│   ├── README.md
│   └── .gitignore
├── README.md
└── PROVENANCE.md
```

Reference: Hugging Face `neurodeskorg/skills-comm-ground-truth`, path `clinical_gt/clinical-stroke-lesion-segmentation/`.
