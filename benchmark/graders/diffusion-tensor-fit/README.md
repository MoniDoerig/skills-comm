# Grader: `diffusion-tensor-fit`

Grades **FA and MD maps from a diffusion tensor fit** against a consensus of defensible fits
of the same acquisition.

## The reference

Each case's acquisition is staged for the agent by the harness from the gated reference
dataset
[`neurodeskorg/skills-comm-ground-truth`](https://huggingface.co/datasets/neurodeskorg/skills-comm-ground-truth).
The reference of a control is the voxelwise median FA and MD of six fits of that staged
acquisition: FSL dtifit and MRtrix3 dwi2tensor, with ordinary and weighted least squares,
on all shells and on b <= 1200 only. Those choices move the level of FA and MD (the panel's
median MD differs by half between shell choices) far more than the pattern, so the maps are
graded mainly on pattern.

The metrics are read inside the b0 brain mask eroded by two voxels, away from the brain's
edge, where partial volume dominates.

## Scorer

```bash
# fetch the case's reference (see reference/README.md), then:
python3 score_tensor_fit.py --submission submissions/diffusion-tensor-fit/<case>/ --pack . [--json result.json]
```

The submission is the case's output directory: `output.nii.gz` (FA) and `md.nii.gz` (MD).

## Metrics

Weighted quality:

- **fa_agreement** (0.50): Pearson r between the FA map and the consensus FA
- **fa_level** (0.20): median absolute difference from the consensus FA
- **md_agreement** (0.30): Pearson r between the MD map and the consensus MD. r ignores
  scale, so mm²/s and µm²/ms read the same. A missing MD map scores 0 here.

Each metric earns full credit at the panel's own leave-one-out spread, widened by a slack
(calibrated per subject, gated), and none at a fixed line from the policy, linearly between.

## Validity gates

- **fa_present**: `output.nii.gz` is there and loads
- **geometry_matches**: it is on the acquisition's grid, with the same shape and affine
- **fa_in_range**: FA inside the brain lies in [0, 1] (up to 1 % of voxels may fall
  outside it) and is not constant

## Verdicts

`within_reference_variability` ≥ 99.9 (every metric at full credit), `acceptable` ≥ 60,
`marginal` ≥ 30, else `unacceptable`; any gate failure is `invalid`. The reasons are in
[`rubrics/policy.json`](rubrics/policy.json).

## Cases whose input cannot support a fit

Some cases of this task carry a role in the gated `cases.json`. On a case whose input
cannot support a fit, `grade_wrapper.py` grades the run report every run writes
([`benchmark/harness/run_report.md`](../../harness/run_report.md)) and never calls this
scorer.
