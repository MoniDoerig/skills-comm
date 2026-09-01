# Reference data

- **OSF project:** zjqey — https://osf.io/zjqey/
- **Path:** `ground_truth/clinical_gt/clinical-ms-lesion-segmentation/`
- **Files:**
  - `lesion_mask.nii.gz` — expert multi-rater consensus MS lesion mask (open_ms_data `patient01`,
    cross-sectional, co-registered + 1 mm resampled FLAIR grid), binarised to {0,1}

Fetch before grading:

    osf -p zjqey fetch osfstorage/ground_truth/clinical_gt/clinical-ms-lesion-segmentation/lesion_mask.nii.gz lesion_mask.nii.gz

The mask is redistributable: the Ljubljana MS database is released under CC-BY, so cite
Lesjak et al., Neuroinformatics 16:51-63 (2018) with any use.
