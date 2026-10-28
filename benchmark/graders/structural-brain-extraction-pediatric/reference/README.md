# Reference data

The frozen reference for this grader is on the Hugging Face Hub:

- **Dataset:** `neurodeskorg/skills-comm-ground-truth`
- **Path:** `structural_gt/structural-brain-extraction-pediatric/<subject>/`
- **Revision:** `f0229ea2b089`
- **Files:**
  - `consensus_mask.nii.gz` — binary STAPLE consensus (native T1w grid)
  - `consensus_zones.nii.gz` — 0 = background, 1 = margin, 2 = core

The reference is one directory per subject; `fetch_reference.py --subject`
pulls the one being graded.

Fetch it into this directory before grading:

    python benchmark/harness/fetch_reference.py --task structural-brain-extraction-pediatric --subject <subject>

Access is gated: request it on the dataset page, then set `HF_TOKEN` to a token for the account
that was granted access. Gating is what keeps the reference out of the plane where the agent works.
Pinning the revision means a grading run scores against an exact, named reference set.

`rubric.json` carries every calibrated number the grader needs.
