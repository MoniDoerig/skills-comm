# Reference data

The frozen reference for this grader is on the Hugging Face Hub:

- **Dataset:** `neurodeskorg/skills-comm-ground-truth`
- **Path:** `clinical_gt/clinical-ms-lesion-segmentation/`
- **Revision:** `f0229ea2b089`
- **Files:**
  - `lesion_mask.nii.gz` — expert multi-rater consensus MS lesion mask (open_ms_data `patient01`,

Fetch them into this directory before grading:

    python benchmark/harness/fetch_reference.py --task clinical-ms-lesion-segmentation

Access is gated: request it on the dataset page, then set `HF_TOKEN` to a token for the account
that was granted access. Gating is what keeps the reference out of the plane where the agent works.
Pinning the revision means a grading run scores against an exact, named reference set.

`rubric.json` carries every calibrated number the grader needs.
