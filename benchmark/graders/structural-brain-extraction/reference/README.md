# Reference data

The frozen reference for this grader is on the Hugging Face Hub:

- **Dataset:** `neurodeskorg/skills-comm-ground-truth`
- **Path:** `structural_gt/structural-brain-extraction/`
- **Revision:** `f0229ea2b089`
- **Files:**
  - `consensus_mask.nii.gz` — binary STAPLE consensus (native T1w grid)
  - `consensus_zones.nii.gz` — 0 = background, 1 = margin, 2 = core

Fetch them into this directory before grading:

    python benchmark/harness/fetch_reference.py --task structural-brain-extraction

The dataset is public, so no token is required. Pinning the revision means a
grading run scores against an exact, named reference set.

`rubric.json` carries every calibrated number the grader needs.
