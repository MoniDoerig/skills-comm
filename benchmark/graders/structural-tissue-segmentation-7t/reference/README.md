# Reference data

The frozen reference for this grader is on the Hugging Face Hub:

- **Dataset:** `neurodeskorg/skills-comm-ground-truth`
- **Path:** `structural_gt/structural-tissue-segmentation-7t/`
- **Revision:** `f0229ea2b089`
- **Files:**
  - `consensus_seg.nii.gz` — fused 6-class label map (native T1w grid); 1=GM 2=basal_ganglia 3=WM 4=ventricles 5=cerebellum 6=brainstem
  - `consensus_agreement.nii.gz` — per-voxel #tools backing the label (3 = unanimous core, 2 = majority)

Fetch them into this directory before grading:

    python benchmark/harness/fetch_reference.py --task structural-tissue-segmentation-7t

The dataset is public, so no token is required. Pinning the revision means a
grading run scores against an exact, named reference set.

`rubric.json` carries every calibrated number the grader needs.
