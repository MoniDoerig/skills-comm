# Reference data

The frozen reference for this grader is on the Hugging Face Hub:

- **Dataset:** `neurodeskorg/skills-comm-ground-truth`
- **Path:** `diffusion_gt/diffusion-brain-mask/<subject>/`
- **Revision:** `f0229ea2b089`
- **Files:**
  - `consensus_mask.nii.gz` — STAPLE consensus of SynthStrip, HD-BET and AFNI 3dSkullStrip,
    on the diffusion grid of ds001226 sub-CON02 ses-preop acq-AP
  - `consensus_zones.nii.gz` — 0 = background, 1 = margin, 2 = core

The reference is one directory per subject; `fetch_reference.py --subject`
pulls the one being graded.

Fetch it into this directory before grading:

    python benchmark/harness/fetch_reference.py --task diffusion-brain-mask --subject <subject>

Access is gated: request it on the dataset page, then set `HF_TOKEN` to a token for the account
that was granted access. Gating is what keeps the reference out of the plane where the agent works.
Pinning the revision means a grading run scores against an exact, named reference set.

`rubric.json` carries every calibrated number the grader needs.
