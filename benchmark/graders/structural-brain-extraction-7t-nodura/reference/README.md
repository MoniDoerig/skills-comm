# Reference data (fetched from OSF, not stored in git)

The frozen reference for this grader lives on OSF, not in this repo
(policy: **code on GitHub, data on OSF**):

- **OSF project:** zjqey — https://osf.io/zjqey/
- **Path:** `ground_truth/structural_gt/structural-brain-extraction-7t-nodura/`
- **Files:**
  - `consensus_mask.nii.gz` — binary STAPLE consensus (native T1w grid)
  - `consensus_zones.nii.gz` — 0 = background, 1 = margin, 2 = core
  - `dura_envelope.nii.gz` — dura-out pial envelope; over-inclusion beyond it = dura

Fetch them into this directory before grading:

    osf -p zjqey fetch osfstorage/ground_truth/structural_gt/structural-brain-extraction-7t-nodura/consensus_mask.nii.gz  consensus_mask.nii.gz
    osf -p zjqey fetch osfstorage/ground_truth/structural_gt/structural-brain-extraction-7t-nodura/consensus_zones.nii.gz  consensus_zones.nii.gz
    osf -p zjqey fetch osfstorage/ground_truth/structural_gt/structural-brain-extraction-7t-nodura/dura_envelope.nii.gz  dura_envelope.nii.gz

`rubric.json` (tracked in git) carries every calibrated number the grader needs.
