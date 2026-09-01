# Reference data

- **OSF project:** zjqey — https://osf.io/zjqey/
- **Path:** `ground_truth/structural_gt/structural-brain-extraction-stroke/`
- **Files:**
  - `consensus_mask.nii.gz` — binary STAPLE consensus (native T1w grid)
  - `consensus_zones.nii.gz` — 0 = background, 1 = margin, 2 = core
  - `lesion_mask.nii.gz` — expert lesion mask (registered to T1w), used by the `lesion_retained` gate

Fetch before grading:

    osf -p zjqey fetch osfstorage/ground_truth/structural_gt/structural-brain-extraction-stroke/consensus_mask.nii.gz  consensus_mask.nii.gz
    osf -p zjqey fetch osfstorage/ground_truth/structural_gt/structural-brain-extraction-stroke/consensus_zones.nii.gz consensus_zones.nii.gz
    osf -p zjqey fetch osfstorage/ground_truth/structural_gt/structural-brain-extraction-stroke/lesion_mask.nii.gz     lesion_mask.nii.gz
