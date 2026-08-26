# Grader: `diffusion-brain-mask`

Grades a **brain mask made from a DWI b0** against a consensus of accepted masking tools
(ds001226 `sub-CON02` `ses-preop`, `acq-AP`, 2.5 mm isotropic).

**What it tests: whether the b0 is prepared before it is masked.** On the raw series every
intensity-threshold method loses the same anatomy — cerebellum, temporal poles, brainstem — to
the inferior bias field. Two routes pass: a contrast-agnostic stripper (SynthStrip, HD-BET,
`3dSkullStrip`), or `dwidenoise` + `dwibiascorrect` before `dwi2mask`, which takes that tool from
`invalid` to `indistinguishable`.

## Why a consensus, not one tool

Every masking tool draws a different boundary, and on a b0 the disagreement is larger than on a
T1w. Grading against any single tool would bake in that tool's convention. Instead the pack
carries a STAPLE consensus of three accepted tools split into three zones —

    core (2)        every accepted tool includes it   -> must be kept  (scored)
    margin (1)      the tools legitimately disagree   -> free          (never scored)
    background (0)  no accepted tool includes it      -> must be out   (scored)

— and scores only the two unambiguous zones. Every threshold is calibrated by leave-one-tool-out;
see `PROVENANCE.md`.

## Scorer (shared with the brain-extraction packs)

```bash
# fetch the reference (see reference/README.md), then:
python3 score_brain_mask.py --mask agent_mask.nii.gz --pack . [--json result.json]
```

The submission is a **binary brain mask on the diffusion grid** (96 × 96 × 60, 2.5 mm).

## Metrics

Weighted quality over five metrics, each mapped to [0, 1] by the leave-one-tool-out envelope —
1.0 at the median accepted tool, 0.0 at 1.5× beyond the worst:

- **NSD** within τ = 5.59 mm (0.30) — boundary agreement
- **core recall** (0.25) — brain must not be cut
- **background false-positive fraction** (0.20) — skull and neck must not be retained
- **HD95** (0.15) — worst-case boundary excursion
- **absolute volume error %** (0.10)

Dice is reported but not scored: it is a function of the two directional errors, so scoring it
would weight the same information twice.

Verdict: `indistinguishable` when every metric reaches full marks; else
`acceptable`/`marginal`/`unacceptable` by weighted quality; `invalid` on any gate failure.

## Gates

`binary`, `native_grid`, `nonempty`, `single_component`, `no_internal_holes`,
`volume_plausible` (1020–2290 cm³), `no_catastrophic_core_loss` (≤ 10 % of core),
`no_focal_core_loss` (≤ 55.1 cm³ contiguous), `no_focal_bg_inclusion` (≤ 40 cm³ contiguous),
`stripped_matches_mask`.

**The gates name the failure.** Dice alone would not separate these: `bet -f 0.2` reaches Dice
0.927 while retaining skull, higher than raw `dwi2mask` at 0.924 which loses the cerebellum.

## Validation

The three reference tools score 92–100, and `dwi2mask` after preprocessing reaches 90.5. Every
other candidate is `invalid`, including **FSL BET at its default `-f 0.5`**, **AFNI
`3dAutomask`** and **raw `dwi2mask`**. Perturbing the consensus ranks
monotonically and both two-voxel failures are caught. Full tables in `PROVENANCE.md`.

## Layout

```
diffusion-brain-mask/
├── rubric.json           # calibrated numbers (tau, envelope, weights, gate caps, grid)
├── score_brain_mask.py   # shared scorer, unmodified
├── reference/            # consensus NIfTIs — FETCHED FROM OSF, not in git
│   ├── README.md
│   └── .gitignore
├── README.md
└── PROVENANCE.md
```

Reference on OSF: project zjqey, `ground_truth/diffusion_gt/diffusion-brain-mask/`.
