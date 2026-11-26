# Reference data

Fetched here before grading, from the gated dataset
`neurodeskorg/skills-comm-ground-truth`:

    python benchmark/harness/fetch_reference.py --task functional-task-glm --case <case>

- `consensus_z_<contrast>.nii.gz`: the panel's voxelwise median z map, one per contrast
- `roi_mask.nii.gz`: the BOLD brain mask, where the metrics are read
- `rubric.json`: written by the fetch from this pack's policy and the subject's gated
  calibration

The dataset path and the pinned revision live in
[`benchmark/harness/run_manifest.json`](../../../harness/run_manifest.json), which is what
the fetch reads; they are deliberately not repeated here.

The dataset is gated, which is what keeps the reference out of the plane where the agent
works. Grading reads a token from `HF_TOKEN`; in CI that comes from a repository secret.
Ask the maintainers about access for local use.
