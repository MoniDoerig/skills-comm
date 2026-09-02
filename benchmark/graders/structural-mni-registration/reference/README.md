# Reference data

The frozen reference for this grader is on the Hugging Face Hub:

- **Dataset:** `neurodeskorg/skills-comm-ground-truth`
- **Path:** `structural_gt/structural-mni-registration/`
- **Revision:** `f0229ea2b089`
- **Files:**
  - `template_T1w.nii.gz` — the template, for in-brain image correlation
  - `template_brain_mask.nii.gz` — brain overlap and the correlation region
  - `template_probseg_GM.nii.gz`, `template_probseg_WM.nii.gz`, `template_probseg_CSF.nii.gz` —
  - `template_probseg_WM.nii.gz`
  - `template_probseg_CSF.nii.gz`

Fetch them into this directory before grading:

    python benchmark/harness/fetch_reference.py --task structural-mni-registration

The dataset is public, so no token is required. Pinning the revision means a
grading run scores against an exact, named reference set.

`rubric.json` carries every calibrated number the grader needs.
