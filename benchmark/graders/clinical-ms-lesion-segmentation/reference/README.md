# Reference data

The frozen reference for this grader is on the Hugging Face Hub:

- **Dataset:** `neurodeskorg/skills-comm-ground-truth`
- **Path:** `clinical_gt/clinical-ms-lesion-segmentation/`
- **Revision:** `f0229ea2b089`
- **Files:**
  - `lesion_mask.nii.gz` — expert multi-rater consensus MS lesion mask (open_ms_data `patient01`,

Fetch them into this directory before grading:

    python benchmark/harness/fetch_reference.py --task clinical-ms-lesion-segmentation

The dataset is public, so no token is required. Pinning the revision means a
grading run scores against an exact, named reference set.

`rubric.json` carries every calibrated number the grader needs.
