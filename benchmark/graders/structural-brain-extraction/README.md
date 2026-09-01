# Grader: `structural-brain-extraction`

A **consensus-calibrated grader** for the `structural-brain-extraction` benchmark task — a
more discriminating alternative to grading a skull-strip by *Dice against one reference mask*.

The prompt is tool-agnostic (`tool_mode: agnostic`), so the grader must ask *"is this a competent
brain mask?"*, not *"does it match one specific tool?"*. Every skull-stripper draws a slightly
different boundary and they disagree in a few predictable places (sagittal sinus, tentorium,
brainstem cut-off, sulcal CSF). So instead of one mask, the grader carries a **STAPLE consensus of a
panel of accepted tools**, split into three zones, and scores only the *unambiguous* voxels:

| zone (value) | meaning | scored? |
|---|---|---|
| **core** (2) | every accepted tool includes it | yes — dropping it = brain cut |
| **margin** (1) | the tools legitimately disagree | **no** — legitimate freedom |
| **background** (0) | no accepted tool includes it | yes — including it = skull/dura/neck kept |

Every threshold (the surface tolerance τ, the per-metric pass/fail envelope, the gate caps) was
**calibrated from the data** (leave-one-tool-out), never hand-picked. See [`PROVENANCE.md`](PROVENANCE.md).

## Layout

```
structural-brain-extraction/
├── rubric.json                       # frozen calibration: τ, envelope, weights, gate caps, grid
├── score_brain_mask.py               # the grader — importable score() + CLI
├── reference/                        # consensus NIfTIs — fetched from OSF
│   ├── README.md                     #   OSF location + fetch command
│   └── .gitignore                    #   keeps *.nii.gz out of git
├── README.md
└── PROVENANCE.md
```

The consensus reference (`consensus_mask.nii.gz`, `consensus_zones.nii.gz`) is on **OSF**
(project zjqey, path `ground_truth/structural_gt/structural-brain-extraction/`). Fetch it into
`reference/` before grading (see `reference/README.md`):

```bash
osf -p zjqey fetch osfstorage/ground_truth/structural_gt/structural-brain-extraction/consensus_mask.nii.gz  reference/consensus_mask.nii.gz
osf -p zjqey fetch osfstorage/ground_truth/structural_gt/structural-brain-extraction/consensus_zones.nii.gz reference/consensus_zones.nii.gz
```

The pack is **frozen once** per benchmark subject; scoring a submission never re-calibrates — it
only computes the cheap per-mask metrics against this reference.

## Run it

```bash
python3 score_brain_mask.py --mask agent_mask.nii.gz --pack . \
    [--stripped agent_brain.nii.gz] [--json result.json]
```

Output is JSON: `verdict`, `quality` (0–100), `gate_failures`, `load_notes`, per-metric `metrics`
and `subscores`. Exit code is `0` for a valid submission, `1` if any gate failed — so it drops into
a harness as a pass/fail check. Depends only on `numpy`, `scipy`, `nibabel`.

Two stages: **gates** (any failure ⇒ `invalid`, score 0, gate named) then a **weighted quality**
mapped onto the leave-one-tool-out envelope. The five scored metrics and weights: NSD@τ (0.30),
core recall (0.25), background FP (0.20), HD95 (0.15), volume error (0.10). The gates include the
discriminating **`no_focal_core_loss`** — it fails a mask that cuts one *contiguous* chunk of core
beyond the calibrated cap, which a global core-recall would dilute.

## How it's wired into `benchmark/tasks.json`

The task's grader-only `solution` carries a `grader` block that points here (its `metric`,
`ground_truth`, and `ground_truth_location` describe this consensus grader — the old single-mask
Dice fields were replaced):

```json
"grader": {
  "kind": "consensus-calibrated",
  "pack": "benchmark/graders/structural-brain-extraction/",
  "reference_fetch": "osf -p zjqey fetch osfstorage/ground_truth/structural_gt/structural-brain-extraction/consensus_mask.nii.gz reference/consensus_mask.nii.gz && osf -p zjqey fetch .../consensus_zones.nii.gz reference/consensus_zones.nii.gz",
  "entry": "score_brain_mask.py",
  "invoke": "python3 benchmark/graders/structural-brain-extraction/score_brain_mask.py --mask <AGENT_MASK> --pack benchmark/graders/structural-brain-extraction/",
  "pass_criterion": "verdict != invalid (script exit code 0)"
}
```

A harness fetches the reference (`reference_fetch`), runs `invoke`, and passes the submission when
`verdict != invalid`.

## Test evidence

Scoring the panel + negative controls against this frozen pack gives:

| submission | verdict | quality | why |
|---|---|---|---|
| `anat_hd_bet_bet.nii.gz` (HD-BET) | `indistinguishable` | 99.96 | NSD 0.991, focal 0.0, clean |
| `AFNI_mask_bin.nii.gz` (AFNI, corrected) | `indistinguishable` | 99.78 | native grid, binary |
| `anat_bet_f07_mask.nii.gz` (BET −f 0.7) | **`invalid`** | 0 | `no_focal_core_loss` — 27.5 cm³ contiguous frontal cut |

```
$ python3 score_brain_mask.py --mask anat_bet_f07_mask.nii.gz --pack .
{ "verdict": "invalid", "quality": 0.0, "gate_failures": ["no_focal_core_loss"], ... }
$ echo $?    # 1
```

## Policy knobs

- **Reference panel** (`rubric.json:reference_tools`) — defines the consensus AND every threshold.
  Adding a tool only *loosens* the benchmark, because the core is an intersection.
- **`focal_max_cm3`** — calibrated (`SLACK` × worst held-out focal miss, floored). Larger = more lenient
  on localised cuts.
- **`native_grid` gate** — here a header-only deoblique (AFNI-style) is recovered onto the native grid
  rather than failed; flip to strict if the task should reject any header that doesn't match the input.
