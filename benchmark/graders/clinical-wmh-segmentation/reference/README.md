# Reference data

- **OSF project:** zjqey — https://osf.io/zjqey/
- **Path:** `ground_truth/clinical_gt/clinical-wmh-segmentation/`
- **Files:**
  - `lesion_mask.nii.gz` — primary expert WMH mask (observers O1/O2), native FLAIR space, binary {0,1}

Fetch before grading:

    osf -p zjqey fetch osfstorage/ground_truth/clinical_gt/clinical-wmh-segmentation/lesion_mask.nii.gz lesion_mask.nii.gz
