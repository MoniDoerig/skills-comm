# Reference data

The frozen reference for this grader is on the Hugging Face Hub:

- **Dataset:** `neurodeskorg/skills-comm-ground-truth`
- **Path:** `diffusion_gt/diffusion-brain-mask/`
- **Revision:** `f0229ea2b089`
- **Files:**
  - `consensus_mask.nii.gz` — STAPLE consensus of SynthStrip, HD-BET and AFNI 3dSkullStrip,
    on the diffusion grid of ds001226 sub-CON02 ses-preop acq-AP
  - `consensus_zones.nii.gz` — 0 = background, 1 = margin, 2 = core

Fetch them into this directory before grading:

    python benchmark/harness/fetch_reference.py --task diffusion-brain-mask

The dataset is public, so no token is required. Pinning the revision means a
grading run scores against an exact, named reference set.

`rubric.json` carries every calibrated number the grader needs.
