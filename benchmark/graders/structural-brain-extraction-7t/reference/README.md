# Reference data (fetched from OSF, not stored in git)

The frozen reference for this grader lives on OSF, not in this repo
(policy: **code on GitHub, data on OSF**):

- **OSF project:** zjqey — https://osf.io/zjqey/
- **Path:** `ground_truth/structural_gt/structural-brain-extraction-7t/`
- **Files:**
  - `consensus_mask.nii.gz` — binary STAPLE consensus (native T1w grid)
  - `consensus_zones.nii.gz` — 0 = background, 1 = margin, 2 = core

Fetch them into this directory before grading:

    osf -p zjqey fetch osfstorage/ground_truth/structural_gt/structural-brain-extraction-7t/consensus_mask.nii.gz  consensus_mask.nii.gz
    osf -p zjqey fetch osfstorage/ground_truth/structural_gt/structural-brain-extraction-7t/consensus_zones.nii.gz  consensus_zones.nii.gz

`rubric.json` (tracked in git) carries every calibrated number the grader needs.
