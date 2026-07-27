# Reference data (fetched from OSF, not stored in git)

The frozen consensus reference for this grader lives on OSF, not in this repo
(policy: **code on GitHub, data on OSF**):

- **OSF project:** zjqey — https://osf.io/zjqey/
- **Path:** `ground_truth/structural_gt/structural-brain-extraction/`
- **Files:**
  - `consensus_mask.nii.gz` — binary STAPLE consensus (native T1w grid)
  - `consensus_zones.nii.gz` — 0 = background, 1 = margin, 2 = core

Fetch them into this directory before grading (osfclient is preinstalled on Neurodesk;
otherwise `pip install osfclient`):

    osf -p zjqey fetch osfstorage/ground_truth/structural_gt/structural-brain-extraction/consensus_mask.nii.gz  consensus_mask.nii.gz
    osf -p zjqey fetch osfstorage/ground_truth/structural_gt/structural-brain-extraction/consensus_zones.nii.gz consensus_zones.nii.gz

`rubric.json` (tracked in git) already carries every calibrated number the grader needs;
only these two NIfTIs are fetched.
