# Reference data

The frozen consensus reference for this grader is on OSF:

- **OSF project:** zjqey — https://osf.io/zjqey/
- **Path:** `ground_truth/structural_gt/structural-brain-extraction-motion/`
- **Files:**
  - `consensus_mask.nii.gz` — binary STAPLE consensus (native T1w grid of the motion scan)
  - `consensus_zones.nii.gz` — 0 = background, 1 = margin, 2 = core

Fetch them into this directory before grading:

    osf -p zjqey fetch osfstorage/ground_truth/structural_gt/structural-brain-extraction-motion/consensus_mask.nii.gz  consensus_mask.nii.gz
    osf -p zjqey fetch osfstorage/ground_truth/structural_gt/structural-brain-extraction-motion/consensus_zones.nii.gz consensus_zones.nii.gz

`rubric.json` carries every calibrated number the grader needs.
