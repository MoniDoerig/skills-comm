# Grader: `structural-tissue-segmentation-7t`

A **consensus-calibrated grader** for multi-class brain **parcellation** of a 7T MP2RAGE scan
(CEREBRUM-7T `ds003642`, `sub-025`, 0.63 mm isotropic). It grades a six-structure label map —
grey matter, basal ganglia, white matter, ventricles/CSF, cerebellum, brainstem — against a
consensus of accepted segmentations. Companion to the binary `structural-brain-extraction-7t`
tasks on the same subject.

It is the multi-class analogue of the brain-extraction grader: instead of one binary mask scored
against a STAPLE consensus, each of six classes is scored against a **majority-vote consensus** of
accepted tools, split into per-class **unanimous-core** (all tools agree) and **majority-boundary**
(partial-volume disagreement) zones. Every threshold is calibrated by leave-one-tool-out. See
[`PROVENANCE.md`](PROVENANCE.md).

## Ships its own scorer

Parcellation needs a different scorer from the binary brain-extraction one, so this pack carries
**`score_tissue_seg.py`** (per-class Dice / NSD / core-recall + the multi-class gates):

```bash
# fetch the reference (see reference/README.md), then:
python3 score_tissue_seg.py --seg agent_dseg.nii.gz --pack . [--json result.json]
```

The agent must output an **integer label map** with the fixed legend
`1=GM 2=basal_ganglia 3=WM 4=ventricles 5=cerebellum 6=brainstem` in native T1w space.

## Reference panel

- **Panel = CEREBRUM7T + FreeSurfer v6 + FreeSurfer v7** — the three whole-brain segmentations
  shipped with the dataset that share a common label scheme (per-class Dice 0.75–0.92).
- **Dropped: nighres** — a coherence outlier (its label-3/WM Dice vs the others is 0.09, a different
  label protocol). It is retained as a scored **candidate** (comes out `invalid` on
  `no_class_collapse`), which validates the grader.

No tools are run to build the reference — the panel members are the dataset's own pre-computed
segmentations, fused by majority vote.

## Scoring

- **Per-class metrics:** Dice, NSD (surface agreement within a per-class tolerance `τ`), and
  core-recall (fraction of the unanimous core recovered). Quality = mean of the six per-class
  qualities, each mapped through the LOTO envelope (median = full marks, worst = pass line).
- **Gates (→ `invalid`):** `valid_labels` (integer map, the six classes present), `native_grid`,
  and `no_class_collapse` (every class must recover ≥ 50 % of its unanimous core — catches a
  swapped or missing class, e.g. GM/WM confusion).

## Layout

```
structural-tissue-segmentation-7t/
├── rubric.json              # per-class τ, LOTO envelope, weights, gates
├── score_tissue_seg.py      # the multi-class scorer
├── reference/               # consensus NIfTIs — fetched from the Hub
│   ├── README.md
│   └── .gitignore
├── README.md
└── PROVENANCE.md
```

Reference: Hugging Face `neurodeskorg/skills-comm-ground-truth`, path `structural_gt/structural-tissue-segmentation-7t/`.
The pack is frozen once; scoring never re-calibrates.
