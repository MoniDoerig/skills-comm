# Reference data

The frozen reference for this grader is on the Hugging Face Hub:

- **Dataset:** `neurodeskorg/skills-comm-ground-truth`
- **Path:** `clinical_gt/clinical-wmh-segmentation/`
- **Revision:** `f0229ea2b089`
- **Files:**
  - `lesion_mask.nii.gz` — primary expert WMH mask (observers O1/O2), native FLAIR space, binary {0,1}

Fetch them into this directory before grading:

    python benchmark/harness/fetch_reference.py --task clinical-wmh-segmentation

Access is gated: request it on the dataset page, then set `HF_TOKEN` to a token for the account
that was granted access. Gating is what keeps the reference out of the plane where the agent works.
Pinning the revision means a grading run scores against an exact, named reference set.

`rubric.json` carries every calibrated number the grader needs.
