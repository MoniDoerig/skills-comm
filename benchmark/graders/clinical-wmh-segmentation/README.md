# Grader: `clinical-wmh-segmentation`

Grades **white-matter-hyperintensity (WMH) segmentation** on a FLAIR image against an **expert mask**,
with thresholds **data-derived from inter-rater agreement**. Dementia / small-vessel-disease axis;
companion to `clinical-stroke-lesion-segmentation`.

Subject: **WMH Segmentation Challenge 2017**, Amsterdam/GE3T/100 — a clinical FLAIR with **115 small,
multi-focal WMH foci** (6.3 cm³). This is the case where **Dice alone is misleading** (a small
boundary slip on tiny lesions tanks it) and **lesion-wise detection matters**.

![How a WMH submission is graded: three experts trace the same FLAIR and the primary mask becomes the reference; a submission passes four validity gates, then earns a 0-100 quality score weighting Dice 40%, lesion-wise F1 40% and volume error 20%; altered copies of the expert mask show that dilating by 2 voxels finds every lesion yet scores marginal.](wmh_grading.png)

*Full size: [`wmh_grading.png`](wmh_grading.png). Every number in it comes from this pack's
`rubric.json` and the grader run on the rater masks.*

## Why inter-rater calibration (the upgrade over the stroke task)

The stroke lesion task used *fixed literature* thresholds (one expert tracing, no rater spread). The
WMH Challenge ships **three raters** on this subject (primary O1/O2, plus O3 and O4), so the pass/fail
envelope is **measured, not assumed**: O3 and O4 are scored against the primary, and their metrics set
"full marks" (as good as another expert) and the pass line. See [`PROVENANCE.md`](PROVENANCE.md).

## Scorer (ships in this pack)

```bash
# fetch the reference (see reference/README.md), then:
python3 score_lesion_seg.py --pred agent_wmh.nii.gz --pack . [--json result.json]
```

The submission is a **binary WMH mask in native FLAIR space**. Same scorer as the stroke lesion task
(Dice + lesion-wise detection F1 + volume error); only the reference and the calibrated thresholds
differ. WMH weighting puts **lesion-wise F1 on par with Dice** (0.4 / 0.4 / 0.2) because the lesions
are many and small.

## Data access — fully open, agent-runnable

The images come from **DataverseNL** (DOI `10.34894/AECRSD`) via the open Dataverse access API — a
plain `curl`, no login or Data-Use-Agreement — so an agent can fetch the FLAIR itself. The expert
masks are **grader-side only**; they are never in the agent's input.

## Layout

```
clinical-wmh-segmentation/
├── rubric.json          # inter-rater-derived thresholds, weights, grid; records the O3/O4 metrics
├── score_lesion_seg.py  # Dice + lesion-wise F1 + volume error
├── reference/           # primary expert WMH mask — fetched from the Hub
│   ├── README.md
│   └── .gitignore
├── wmh_grading.png      # the explainer figure above
├── README.md
└── PROVENANCE.md
```

Reference: Hugging Face `neurodeskorg/skills-comm-ground-truth`, path `clinical_gt/clinical-wmh-segmentation/`.

## Verdicts

Best to worst. `quality` is the weighted score in 0–100; the thresholds are in `rubric.json`.

| verdict | meaning |
|---|---|
| `within_reference_variability` | inside the published inter-rater ceiling recorded in `threshold_basis` — the reference is one expert tracing, so there is no panel spread to measure against and the bar comes from the literature |
| `acceptable` | `quality >= 60` |
| `marginal` | `quality >= 30` |
| `unacceptable` | below that |
| `invalid` | a validity gate failed; `quality` is forced to 0 |

A submission passes when the verdict is `within_reference_variability` or `acceptable`.
`within_reference_variability` is the top grade, not a hedge: it says the answer sits
inside the disagreement the reference itself carries, which is as close as this task can
measure.
