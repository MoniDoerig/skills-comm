# Grader: `clinical-wmh-segmentation`

Grades **white-matter-hyperintensity (WMH) segmentation** on a FLAIR image against an **expert mask**,
with thresholds **data-derived from inter-rater agreement**. Dementia / small-vessel-disease axis;
companion to `clinical-stroke-lesion-segmentation`.

Subject: **WMH Segmentation Challenge 2017**, Amsterdam/GE3T/100 — a clinical FLAIR with **115 small,
multi-focal WMH foci** (6.3 cm³). This is the case where **Dice alone is misleading** (a small
boundary slip on tiny lesions tanks it) and **lesion-wise detection matters**.

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
masks are **grader-side only** (OSF); they are never in the agent's input.

## Layout

```
clinical-wmh-segmentation/
├── rubric.json          # inter-rater-derived thresholds, weights, grid; records the O3/O4 metrics
├── score_lesion_seg.py  # Dice + lesion-wise F1 + volume error
├── reference/           # primary expert WMH mask — FETCHED FROM OSF, not in git
│   ├── README.md
│   └── .gitignore
├── README.md
└── PROVENANCE.md
```

Reference on OSF: project zjqey, `ground_truth/clinical_gt/clinical-wmh-segmentation/`.
