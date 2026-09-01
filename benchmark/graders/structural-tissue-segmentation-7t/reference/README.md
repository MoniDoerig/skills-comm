# Reference data

The frozen consensus reference for this grader is on OSF:

- **OSF project:** zjqey — https://osf.io/zjqey/
- **Path:** `ground_truth/structural_gt/structural-tissue-segmentation-7t/`
- **Files:**
  - `consensus_seg.nii.gz` — fused 6-class label map (native T1w grid); 1=GM 2=basal_ganglia 3=WM 4=ventricles 5=cerebellum 6=brainstem
  - `consensus_agreement.nii.gz` — per-voxel #tools backing the label (3 = unanimous core, 2 = majority)

Fetch them into this directory before grading:

    osf -p zjqey fetch osfstorage/ground_truth/structural_gt/structural-tissue-segmentation-7t/consensus_seg.nii.gz        consensus_seg.nii.gz
    osf -p zjqey fetch osfstorage/ground_truth/structural_gt/structural-tissue-segmentation-7t/consensus_agreement.nii.gz  consensus_agreement.nii.gz

`rubric.json` carries every calibrated number the grader needs.
