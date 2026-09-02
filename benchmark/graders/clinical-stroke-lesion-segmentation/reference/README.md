# Reference data

The frozen reference for this grader is on the Hugging Face Hub:

- **Dataset:** `neurodeskorg/skills-comm-ground-truth`
- **Path:** `clinical_gt/clinical-stroke-lesion-segmentation/`
- **Revision:** `f0229ea2b089`
- **Files:**
  - `lesion_mask.nii.gz` — expert manual lesion tracing (ARC), registered to native T1w space

Fetch them into this directory before grading:

    python benchmark/harness/fetch_reference.py --task clinical-stroke-lesion-segmentation

The dataset is public, so no token is required. Pinning the revision means a
grading run scores against an exact, named reference set.

`rubric.json` carries every calibrated number the grader needs.
