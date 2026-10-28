# Reference data

The frozen reference for this grader is on the Hugging Face Hub:

- **Dataset:** `neurodeskorg/skills-comm-ground-truth`
- **Path:** `clinical_gt/clinical-stroke-lesion-segmentation/<subject>/`
- **Revision:** `f0229ea2b089`
- **Files:**
  - `lesion_mask.nii.gz` — expert manual lesion tracing (ARC), registered to native T1w space

The reference is one directory per subject; `fetch_reference.py --subject`
pulls the one being graded.

Fetch it into this directory before grading:

    python benchmark/harness/fetch_reference.py --task clinical-stroke-lesion-segmentation --subject <subject>

Access is gated: request it on the dataset page, then set `HF_TOKEN` to a token for the account
that was granted access. Gating is what keeps the reference out of the plane where the agent works.
Pinning the revision means a grading run scores against an exact, named reference set.

`rubric.json` carries every calibrated number the grader needs.

The thresholds are not here. Each subject's rubric is tracked in the repo at
`../rubrics/<subject>.json`, and the fetch command above copies the one being graded
to `rubric.json` in this directory. Keeping them in git means the grading criteria can
be read without access to the gated data, and they version with the scorer.
