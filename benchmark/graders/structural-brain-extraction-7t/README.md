# Grader: `structural-brain-extraction-7t`

A **consensus-calibrated grader** for skull-stripping a **7 Tesla MP2RAGE** scan
(CEREBRUM-7T `ds003642`, `sub-025`, 0.63 mm isotropic). It is the companion to
`structural-brain-extraction` (healthy 3T baseline) on the **field-strength / sequence axis**.

Same design as the baseline: score a submission against a STAPLE consensus of a tool panel split
into core (must keep) / margin (free, not scored) / background (must exclude), with all thresholds
calibrated from the tools' own disagreement. See [`PROVENANCE.md`](PROVENANCE.md).

## Shared scorer (no duplication)

This pack carries **only the calibration** (`rubric.json`) and the reference pointer — it does
**not** ship its own scorer. Grade with the shared scorer from the baseline pack, pointing `--pack`
here:

```bash
# fetch the reference (see reference/README.md), then:
python3 ../structural-brain-extraction/score_brain_mask.py \
    --mask agent_mask.nii.gz --pack . [--stripped agent_brain.nii.gz] [--json result.json]
```

## What's hard here

The MP2RAGE **UNI** image (BIDS-named `T1w`) has salt-and-pepper noise filling the entire
background — there is no clean air boundary. On top of that the 7T contrast and bias field defeat
intensity-based extraction. The result:

- **Intensity-based `bet` fails catastrophically** — it retains ~557 cm³ (roughly half a brain),
  tripping `volume_plausible` + `no_catastrophic_core_loss` → `invalid`. This holds whether or not
  the background is cleaned first, so it is a genuine tool-choice failure, not a preprocessing slip.
- **Contrast-robust deep-learning tools succeed on the raw image** — SynthStrip and HD-BET both
  score `within_reference_variability` on the uncleaned UNI. A competent agent reaches for one of these (or
  denoises the UNI via the INV2 image first).

So this task discriminates on **tool choice for a high-field sequence**, where the common `bet`
default is the wrong call.

## Reference panel

Run on the cleaned UNI, then curated by the coherence check:

- **Panel = HD-BET + AFNI + SynthStrip** (pairwise Dice 0.87–0.93).
- **Dropped: FSL BET -R** — catastrophic outlier at 7T (546 cm³, mean pairwise Dice 0.64). It is
  retained as a scored **candidate** (comes out `invalid`), which validates the grader.
- **τ ≈ 13.4 mm** — wide, because SynthStrip keeps a thick CSF rim at 7T. The task's discriminating
  power is in the **validity gates** (which reject the `bet` failure), not the quality envelope.

## Layout

```
structural-brain-extraction-7t/
├── rubric.json          # frozen calibration: τ, envelope, weights, gate caps, grid.raw_affine
├── reference/           # consensus NIfTIs — fetched from the Hub
│   ├── README.md        #   dataset path + fetch command
│   └── .gitignore
├── README.md
└── PROVENANCE.md
```

Reference: Hugging Face `neurodeskorg/skills-comm-ground-truth`, path `structural_gt/structural-brain-extraction-7t/`.
The pack is frozen once; scoring never re-calibrates.

## Verdicts

Best to worst. `quality` is the weighted score in 0–100; the thresholds are in `rubrics/<subject>.json`.

| verdict | meaning |
|---|---|
| `within_reference_variability` | inside the panel's own leave-one-tool-out spread — every metric is at least as good as the weakest the reference tools themselves achieve, so the submission cannot be told apart from a panel member |
| `acceptable` | `quality >= 60` |
| `marginal` | `quality >= 30` |
| `unacceptable` | below that |
| `invalid` | a validity gate failed; `quality` is forced to 0 |

A submission passes when the verdict is `within_reference_variability` or `acceptable`.
`within_reference_variability` is the top grade, not a hedge: it says the answer sits
inside the disagreement the reference itself carries, which is as close as this task can
measure.
