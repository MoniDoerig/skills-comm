# Grader: `functional-task-glm`

Grades the **z maps of a first-level task GLM** of the finger-foot-lips motor task against a
consensus of independent GLM packages on the same preprocessed BOLD.

## The reference

Each case's files are staged for the agent by the harness from the gated reference dataset
[`neurodeskorg/skills-comm-ground-truth`](https://huggingface.co/datasets/neurodeskorg/skills-comm-ground-truth):
the fMRIPrep-preprocessed BOLD in MNI152NLin2009cAsym at 2 mm, its brain mask, sidecar and
confounds, and the task's events. The reference of a case is the voxelwise median z map, per
contrast, of four first-level GLMs of that BOLD: nilearn, FSL FEAT, SPM12 and AFNI
(3dDeconvolve with 3dREMLfit). Each package keeps its own conventions for smoothing (4 to
8 mm), HRF, drift and noise model, with the same events and eight nuisance regressors. Those
choices move the scale and smoothness of a z map far more than where the activation lies,
so the maps are graded on pattern.

The metrics are read inside the BOLD brain mask.

## Scorer

```bash
# fetch the case's reference (see reference/README.md), then:
python3 score_task_glm.py --submission submissions/functional-task-glm/<case>/ --pack . [--json result.json]
```

The submission is the case's output directory with six maps: `z_finger.nii.gz`,
`z_foot.nii.gz`, `z_lips.nii.gz` (each movement against rest) and
`z_finger_vs_others.nii.gz`, `z_foot_vs_others.nii.gz`, `z_lips_vs_others.nii.gz` (each
movement against the mean of the other two).

## Metrics

Weighted quality, one metric per contrast: the Pearson r between the submitted map and the
consensus map. r reads a t map or an effect-size map as it reads a z map.

- the three **movement-vs-others** maps, 0.18 each: they hold the somatotopy
- the three **movement-vs-rest** maps, 0.1533 each: they share most of their pattern. A
  missing or off-grid one scores 0 here.

Each metric earns full credit at the panel's own leave-one-out spread, lowered by a slack
(calibrated per subject, gated), and none at a fixed line from the policy, linearly between.

## Validity gates

- **maps_present**: the three movement-vs-others maps are there and load
- **geometry_matches**: they are on the BOLD grid, with the same shape and affine
- **maps_vary**: none is constant inside the brain
- **contrast_identity**: each movement-vs-others map agrees best with its own consensus,
  not another movement's (swapped condition labels fail here)

## Verdicts

`within_reference_variability` ≥ 99.9 (every contrast at full credit), `acceptable` ≥ 60,
`marginal` ≥ 30, else `unacceptable`; any gate failure is `invalid`. The reasons are in
[`rubrics/policy.json`](rubrics/policy.json).
