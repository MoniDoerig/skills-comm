# Reference data

The frozen reference for this grader is on the Hugging Face Hub:

- **Dataset:** `neurodeskorg/skills-comm-ground-truth`
- **Path:** `clinical_gt/clinical-wmh-segmentation/`
- **Revision:** `f0229ea2b089`
- **Files:**
  - `lesion_mask.nii.gz` — primary expert WMH mask (observers O1/O2), native FLAIR space, binary {0,1}

Fetch them into this directory before grading:

    python benchmark/harness/fetch_reference.py --task clinical-wmh-segmentation

The dataset is public, so no token is required. Pinning the revision means a
grading run scores against an exact, named reference set.

`rubric.json` carries every calibrated number the grader needs.
