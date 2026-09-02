# Reference data

The frozen reference for this grader is on the Hugging Face Hub:

- **Dataset:** `neurodeskorg/skills-comm-ground-truth`
- **Path:** `fmri_gt/functional-bold-to-mni/`
- **Revision:** `f0229ea2b089`
- **Files:**
  - `template_T1w.nii.gz` — the template, for in-brain mutual information
  - `template_brain_mask.nii.gz` — the region NMI is measured in, and the placement reference

Fetch them into this directory before grading:

    python benchmark/harness/fetch_reference.py --task functional-bold-to-mni

The dataset is public, so no token is required. Pinning the revision means a
grading run scores against an exact, named reference set.

`rubric.json` carries every calibrated number the grader needs.
